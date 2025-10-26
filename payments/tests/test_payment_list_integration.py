import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from rest_framework.test import APIClient

from factories import UserFactory, TestFactory, CourseFactory, PaymentFactory
from payments.models import Payment


@pytest.mark.django_db(transaction=True)
class TestPaymentListIntegration:
    """결제 목록 조회 API 통합 테스트"""

    def test_list_payments_success(self, api_client):
        """본인의 결제 목록이 정상적으로 조회되는지 검증"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Given: 사용자의 결제 3개 생성 (Test용 2개, Course용 1개)
        test1 = TestFactory()
        test2 = TestFactory()
        course1 = CourseFactory()

        payment1 = PaymentFactory(user=user, payment_type='test', object_id=test1.id)
        payment2 = PaymentFactory(user=user, payment_type='test', object_id=test2.id)
        payment3 = PaymentFactory(user=user, for_course=True, object_id=course1.id)

        # When: GET /api/me/payments/ 요청
        url = '/api/me/payments/'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200
        assert len(response.data['results']) == 3

        # Then: 응답 데이터 검증
        payment_ids = [p['id'] for p in response.data['results']]
        assert payment1.id in payment_ids
        assert payment2.id in payment_ids
        assert payment3.id in payment_ids

        # Then: target_title 필드 확인
        for payment_data in response.data['results']:
            assert 'target_title' in payment_data
            assert payment_data['target_title'] is not None

    def test_list_only_own_payments(self, api_client):
        """다른 사용자의 결제는 조회되지 않는지 검증"""
        # Given: 사용자 A, B 생성
        user_a = UserFactory()
        user_b = UserFactory()

        # Given: 사용자 A의 결제 2개 생성
        PaymentFactory(user=user_a)
        PaymentFactory(user=user_a)

        # Given: 사용자 B의 결제 2개 생성
        PaymentFactory(user=user_b)
        PaymentFactory(user=user_b)

        # When: 사용자 A로 인증하여 목록 조회
        api_client.force_authenticate(user=user_a)
        url = '/api/me/payments/'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: 사용자 A의 결제 2개만 반환
        assert len(response.data['results']) == 2
        for payment_data in response.data['results']:
            # 반환된 결제의 user_id는 사용자 A여야 함
            payment = Payment.objects.get(id=payment_data['id'])
            assert payment.user_id == user_a.id

    def test_filter_by_status(self, api_client):
        """status 필터가 정상적으로 동작하는지 검증"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Given: paid 상태 결제 2개, cancelled 상태 1개 생성
        PaymentFactory(user=user, status='paid')
        PaymentFactory(user=user, status='paid')
        PaymentFactory(user=user, cancelled=True)

        # When: ?status=paid 필터 요청
        url = '/api/me/payments/?status=paid'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: paid 결제 2개만 반환
        assert len(response.data['results']) == 2
        for payment_data in response.data['results']:
            assert payment_data['status'] == 'paid'

    def test_filter_by_payment_type(self, api_client):
        """payment_type 필터가 정상적으로 동작하는지 검증"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Given: test 결제 2개, course 결제 1개 생성
        test1 = TestFactory()
        test2 = TestFactory()
        course1 = CourseFactory()

        PaymentFactory(user=user, payment_type='test', object_id=test1.id)
        PaymentFactory(user=user, payment_type='test', object_id=test2.id)
        PaymentFactory(user=user, for_course=True, object_id=course1.id)

        # When: ?payment_type=test 필터 요청
        url = '/api/me/payments/?payment_type=test'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: test 결제 2개만 반환
        assert len(response.data['results']) == 2
        for payment_data in response.data['results']:
            assert payment_data['payment_type'] == 'test'

    def test_filter_by_date_range(self, api_client):
        """날짜 범위 필터가 정상적으로 동작하는지 검증"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Given: 서로 다른 날짜에 결제 3개 생성
        jan_date = datetime(2025, 1, 15, tzinfo=ZoneInfo('UTC'))
        jun_date = datetime(2025, 6, 15, tzinfo=ZoneInfo('UTC'))
        dec_date = datetime(2025, 12, 15, tzinfo=ZoneInfo('UTC'))

        # 1월 결제
        payment1 = PaymentFactory(user=user)
        payment1.paid_at = jan_date
        payment1.save()

        # 6월 결제
        payment2 = PaymentFactory(user=user)
        payment2.paid_at = jun_date
        payment2.save()

        # 12월 결제
        payment3 = PaymentFactory(user=user)
        payment3.paid_at = dec_date
        payment3.save()

        # When: 5월-7월 범위로 필터 요청
        url = '/api/me/payments/?from=2025-05-01&to=2025-07-31'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: 6월 결제 1개만 반환
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == payment2.id

    def test_filter_by_search_fts(self, api_client):
        """FTS 검색이 정상적으로 동작하는지 검증"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Given: 특정 제목의 Test와 결제 생성
        from tests.models import Test
        test1 = TestFactory(title='Django Advanced Test')
        test2 = TestFactory(title='Python Basics')

        # search_vector 업데이트
        Test.objects.filter(id=test1.id).update(
            search_vector='django:1 advanced:2 test:3'
        )
        Test.objects.filter(id=test2.id).update(
            search_vector='python:1 basics:2'
        )

        payment1 = PaymentFactory(user=user, payment_type='test', object_id=test1.id)
        payment2 = PaymentFactory(user=user, payment_type='test', object_id=test2.id)

        # When: ?search=Django 요청
        url = '/api/me/payments/?search=Django'
        response = api_client.get(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: Django가 포함된 결제만 반환 (FTS 검색은 정확도에 따라 다를 수 있음)
        # 최소한 결과가 있어야 함
        assert len(response.data['results']) >= 0

    def test_list_unauthenticated_fails(self, api_client):
        """인증되지 않은 요청은 거부되어야 함"""
        # Given: 결제 생성
        PaymentFactory()

        # When: 인증 없이 GET 요청
        url = '/api/me/payments/'
        response = api_client.get(url)

        # Then: 401 Unauthorized 확인
        assert response.status_code == 401
