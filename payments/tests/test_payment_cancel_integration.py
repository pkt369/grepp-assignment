import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone
from rest_framework.test import APIClient

from factories import (
    UserFactory, TestFactory, CourseFactory, PaymentFactory,
    TestRegistrationFactory, CourseRegistrationFactory
)
from payments.models import Payment
from tests.models import TestRegistration
from courses.models import CourseRegistration


@pytest.mark.django_db(transaction=True)
class TestPaymentCancelIntegration:
    """결제 취소 API 통합 테스트"""

    def test_cancel_payment_success_deletes_test_registration(self, api_client):
        """Test 결제 취소 시 Payment 상태가 변경되고 TestRegistration이 삭제되는지 검증"""
        # Given: 사용자, 시험, Payment, TestRegistration 생성
        user = UserFactory()
        test = TestFactory()

        # Payment 생성 (GenericForeignKey로 test 연결)
        payment = PaymentFactory(
            user=user,
            payment_type='test',
            object_id=test.id
        )

        # TestRegistration 생성
        registration = TestRegistrationFactory(user=user, test=test)

        # When: 결제 취소 요청
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 200 OK 확인
        assert response.status_code == 200
        assert response.data['message'] == '결제가 취소되었습니다'
        assert response.data['payment_id'] == payment.id
        assert 'cancelled_at' in response.data

        # Then: Payment 상태가 'cancelled'로 변경되었는지 확인
        payment.refresh_from_db()
        assert payment.status == 'cancelled'
        assert payment.cancelled_at is not None

        # Then: TestRegistration이 삭제되었는지 확인
        assert not TestRegistration.objects.filter(id=registration.id).exists()

    def test_cancel_payment_success_deletes_course_enrollment(self, api_client):
        """Course 결제 취소 시 Payment 상태가 변경되고 CourseRegistration이 삭제되는지 검증"""
        # Given: 사용자, 수업, Payment, CourseRegistration 생성
        user = UserFactory()
        course = CourseFactory()

        # Payment 생성 (GenericForeignKey로 course 연결)
        payment = PaymentFactory(
            user=user,
            payment_type='course',
            object_id=course.id,
            for_course=True
        )

        # CourseRegistration 생성
        registration = CourseRegistrationFactory(user=user, course=course)

        # When: 결제 취소 요청
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 200 OK 확인
        assert response.status_code == 200
        assert response.data['message'] == '결제가 취소되었습니다'

        # Then: Payment 상태가 'cancelled'로 변경되었는지 확인
        payment.refresh_from_db()
        assert payment.status == 'cancelled'
        assert payment.cancelled_at is not None

        # Then: CourseRegistration이 삭제되었는지 확인
        assert not CourseRegistration.objects.filter(id=registration.id).exists()

    def test_cancel_unauthenticated_fails(self, api_client):
        """인증되지 않은 요청은 거부되어야 함"""
        # Given: Payment 생성
        payment = PaymentFactory()

        # When: 인증 없이 취소 요청
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 401 Unauthorized 확인
        assert response.status_code == 401

    def test_cancel_other_user_payment_fails(self, api_client):
        """다른 사용자의 결제는 취소할 수 없어야 함"""
        # Given: 사용자 A의 Payment 생성
        user_a = UserFactory()
        payment = PaymentFactory(user=user_a)

        # Given: 사용자 B로 인증
        user_b = UserFactory()
        api_client.force_authenticate(user=user_b)

        # When: 사용자 B가 사용자 A의 결제 취소 시도
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 403 Forbidden 확인 (본인의 결제만 취소 가능)
        assert response.status_code == 403

    def test_cancel_already_cancelled_payment_fails(self, api_client):
        """이미 취소된 결제는 다시 취소할 수 없어야 함"""
        # Given: 이미 취소된 Payment 생성
        user = UserFactory()
        payment = PaymentFactory(user=user, cancelled=True)

        # When: 취소 요청
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 400 Bad Request 확인
        assert response.status_code == 400
        assert '이미 취소된 결제입니다' in response.data['error']

    def test_cancel_already_refunded_payment_fails(self, api_client):
        """이미 환불된 결제는 취소할 수 없어야 함"""
        # Given: 환불된 Payment 생성
        user = UserFactory()
        payment = PaymentFactory(user=user, status='refunded')

        # When: 취소 요청
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 400 Bad Request 확인
        assert response.status_code == 400
        assert '이미 취소된 결제입니다' in response.data['error']

    def test_cancel_concurrent_requests_only_one_succeeds(self):
        """Redis Lock이 동시 취소 요청을 올바르게 제어하는지 검증"""
        # Given: 사용자, 시험, Payment, TestRegistration 생성
        user = UserFactory()
        test = TestFactory()
        payment = PaymentFactory(
            user=user,
            payment_type='test',
            object_id=test.id
        )
        registration = TestRegistrationFactory(user=user, test=test)

        user_id = user.id
        payment_id = payment.id
        registration_id = registration.id

        # When: ThreadPoolExecutor를 사용하여 동시에 10개 취소 요청 전송
        def make_request():
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # 각 스레드에서 독립적으로 user 객체를 조회
            thread_user = User.objects.get(id=user_id)

            client = APIClient()
            client.force_authenticate(user=thread_user)
            url = f'/api/payments/{payment_id}/cancel/'
            return client.post(url)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # Then: 성공(200)은 정확히 1개만 확인
        # 나머지는 400(이미 취소됨) 또는 409(Lock 획득 실패)
        success_count = sum(1 for r in results if r.status_code == 200)
        failure_count = sum(1 for r in results if r.status_code in [400, 409])

        # 중요: 성공은 반드시 1개만, 나머지는 실패해야 함
        assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
        assert failure_count == 9, f"Expected exactly 9 failures (400 or 409), got {failure_count}"
        assert success_count + failure_count == 10, "Total requests should be 10"

        # Then: Payment 상태가 'cancelled'인지 확인
        payment.refresh_from_db()
        assert payment.status == 'cancelled'
        assert payment.cancelled_at is not None

        # Then: TestRegistration이 삭제되었는지 확인
        assert not TestRegistration.objects.filter(id=registration_id).exists()

    def test_cancel_without_registration(self, api_client):
        """Registration이 없어도 Payment 취소 가능한지 검증"""
        # Given: Payment만 생성 (Registration 없음)
        user = UserFactory()
        test = TestFactory()
        payment = PaymentFactory(
            user=user,
            payment_type='test',
            object_id=test.id
        )

        # When: 취소 요청
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 200 OK 확인
        assert response.status_code == 200
        assert response.data['message'] == '결제가 취소되었습니다'

        # Then: Payment 상태가 'cancelled'로 변경되었는지 확인
        payment.refresh_from_db()
        assert payment.status == 'cancelled'
        assert payment.cancelled_at is not None
