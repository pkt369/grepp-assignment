import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from courses.models import Course, CourseRegistration
from factories import UserFactory, CourseFactory, CourseRegistrationFactory
from payments.models import Payment


@pytest.mark.django_db(transaction=True)
class TestCourseEnrollIntegration:
    """수업 수강 신청 API 통합 테스트"""

    def test_enroll_success_creates_payment_and_registration(self, api_client):
        """정상적인 수강 신청 시 Payment와 CourseRegistration이 생성되는지 검증"""
        # Given: 사용자와 수업 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # When: API Client 인증 설정 및 유효한 데이터로 POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 201 Created 응답 확인
        assert response.status_code == 201
        assert 'payment_id' in response.data
        assert 'enrollment_id' in response.data
        assert response.data['message'] == '수업 수강 신청이 완료되었습니다'

        # Then: DB에서 Payment 객체가 생성되었는지 확인
        payment = Payment.objects.get(id=response.data['payment_id'])
        assert payment.user == user
        assert payment.amount == Decimal('50000.00')
        assert payment.payment_method == 'card'
        assert payment.status == 'paid'
        assert payment.payment_type == 'course'
        assert payment.object_id == course.id

        # Then: DB에서 CourseRegistration 객체가 생성되었는지 확인
        enrollment = CourseRegistration.objects.get(id=response.data['enrollment_id'])
        assert enrollment.user == user
        assert enrollment.course == course
        assert enrollment.status == 'enrolled'

    def test_enroll_success_with_different_payment_methods(self, api_client):
        """모든 결제 수단이 정상 작동하는지 검증"""
        payment_methods = ['kakaopay', 'card', 'bank_transfer']

        for method in payment_methods:
            # Given: 사용자와 수업 생성
            user = UserFactory()
            course = CourseFactory(price=Decimal('50000.00'))

            # When: 각 결제 수단으로 POST 요청
            api_client.force_authenticate(user=user)
            url = f'/api/courses/{course.id}/enroll/'
            data = {
                'amount': '50000.00',
                'payment_method': method
            }
            response = api_client.post(url, data, format='json')

            # Then: 201 Created 응답 확인
            assert response.status_code == 201

            # Then: Payment의 payment_method가 올바르게 저장되었는지 확인
            payment = Payment.objects.get(id=response.data['payment_id'])
            assert payment.payment_method == method

    def test_enroll_fails_when_unauthenticated(self, api_client):
        """인증되지 않은 요청은 거부되어야 함"""
        # Given: 수업 생성
        course = CourseFactory(price=Decimal('50000.00'))

        # When: 인증 없이 POST 요청
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 401 Unauthorized 응답 확인
        assert response.status_code == 401

        # Then: DB에 Payment, CourseRegistration이 생성되지 않았는지 확인
        assert Payment.objects.count() == 0
        assert CourseRegistration.objects.count() == 0

    def test_enroll_fails_when_course_not_found(self, api_client):
        """존재하지 않는 수업에 대한 요청은 404 반환"""
        # Given: 사용자 생성 및 인증
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # When: 존재하지 않는 course_id로 POST 요청
        url = '/api/courses/99999/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 404 Not Found 응답 확인
        assert response.status_code == 404

    def test_enroll_fails_when_duplicate_registration(self, api_client):
        """중복 수강 신청은 거부되어야 함"""
        # Given: 사용자, 수업, CourseRegistration 생성 (이미 신청된 상태)
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))
        CourseRegistrationFactory(user=user, course=course)

        # When: 동일한 수업에 재신청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '이미 수강 신청한 수업입니다' in response.data['error']

        # Then: Payment, CourseRegistration 개수가 증가하지 않았는지 확인
        assert Payment.objects.count() == 0
        assert CourseRegistration.objects.filter(user=user, course=course).count() == 1

    def test_enroll_fails_when_not_available_period(self, api_client):
        """수강 가능 기간이 아닌 수업은 신청 불가"""
        # Given: 미래 날짜 수업 생성
        user = UserFactory()
        course = CourseFactory(
            price=Decimal('50000.00'),
            start_at=timezone.now() + timedelta(days=365),
            end_at=timezone.now() + timedelta(days=730)
        )

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '현재 수강 가능한 기간이 아닙니다' in response.data['error']

    def test_enroll_fails_when_amount_mismatch(self, api_client):
        """결제 금액이 수업 가격과 다르면 거부"""
        # Given: 수업 생성 (price=50000)
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # When: 다른 금액으로 POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '60000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '결제 금액이 수업 가격과 일치하지 않습니다' in response.data['error']

    def test_enroll_fails_when_invalid_payment_method(self, api_client):
        """잘못된 결제 수단은 거부"""
        # Given: 수업 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # When: 잘못된 payment_method로 POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'invalid_method'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert 'payment_method' in response.data

    def test_enroll_fails_when_missing_required_fields(self, api_client):
        """필수 필드 누락 시 거부"""
        # Given: 수업 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'

        # When: amount 없이 POST 요청
        data = {'payment_method': 'card'}
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert 'amount' in response.data

        # When: payment_method 없이 POST 요청
        data = {'amount': '50000.00'}
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert 'payment_method' in response.data

    def test_enroll_fails_when_negative_amount(self, api_client):
        """음수 금액은 거부"""
        # Given: 수업 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # When: 음수 금액으로 POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '-1000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400

    def test_enroll_prevents_duplicate_with_concurrent_requests(self):
        """Redis Lock이 동시 요청을 올바르게 제어하는지 검증"""
        # Given: 사용자와 수업 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))
        user_id = user.id
        course_id = course.id

        # When: ThreadPoolExecutor를 사용하여 동시에 10개 요청 전송
        def make_request():
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # 각 스레드에서 독립적으로 user 객체를 조회
            thread_user = User.objects.get(id=user_id)

            client = APIClient()
            client.force_authenticate(user=thread_user)
            url = f'/api/courses/{course_id}/enroll/'
            data = {
                'amount': '50000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # Then: 성공 응답(201)은 정확히 1개만 확인
        success_count = sum(1 for r in results if r.status_code == 201)
        failure_count = sum(1 for r in results if r.status_code in [400, 409])
        error_count = sum(1 for r in results if r.status_code >= 500)

        assert success_count == 1, f"Expected 1 success, got {success_count}"
        # 실패(400, 409) + 에러(500)의 합이 9개여야 함
        assert failure_count + error_count == 9, f"Expected 9 failures, got {failure_count} failures + {error_count} errors"

        # Then: DB에 Payment가 1개만 생성되었는지 확인
        assert Payment.objects.filter(user_id=user_id, object_id=course_id).count() == 1
        # Then: DB에 CourseRegistration이 1개만 생성되었는지 확인
        assert CourseRegistration.objects.filter(user_id=user_id, course_id=course_id).count() == 1

    def test_enroll_allows_different_users_concurrently(self):
        """서로 다른 사용자는 동시에 같은 수업에 등록 가능"""
        # Given: 여러 사용자와 하나의 수업 생성
        users = [UserFactory() for _ in range(5)]
        course = CourseFactory(price=Decimal('50000.00'))
        course_id = course.id

        # When: 각 사용자가 동시에 등록
        def make_request(user_id):
            from django.contrib.auth import get_user_model
            User = get_user_model()

            thread_user = User.objects.get(id=user_id)
            client = APIClient()
            client.force_authenticate(user=thread_user)
            url = f'/api/courses/{course_id}/enroll/'
            data = {
                'amount': '50000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, user.id) for user in users]
            results = [future.result() for future in as_completed(futures)]

        # Then: 모든 요청이 성공해야 함
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 5

        # Then: DB에 5개의 등록이 생성되었는지 확인
        assert CourseRegistration.objects.filter(course_id=course_id).count() == 5
