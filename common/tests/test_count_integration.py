"""
Integration tests for registration count aggregation system.
"""
import pytest
from decimal import Decimal
from rest_framework.test import APIClient

from tests.models import Test, TestRegistration
from courses.models import Course, CourseRegistration
from payments.models import Payment
from factories import UserFactory, TestFactory, CourseFactory
from common.redis_client import get_redis_client
from common.tasks import sync_registration_counts


@pytest.mark.django_db(transaction=True)
class TestApplyIntegrationWithRedis:
    """apply 액션 Redis 통합 테스트"""

    def test_apply_adds_test_id_to_redis(self):
        """apply 성공 시 Redis Set에 test ID가 추가되는지 확인"""
        # Given: 사용자와 test 생성
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When: apply API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/apply/'
        data = {
            'amount': '45000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 201 Created 응답
        assert response.status_code == 201

        # Then: Redis Set에 test ID가 추가되어야 함
        members = client.smembers('test:updated_ids')
        test_id_str = str(test.id).encode() if isinstance(list(members)[0] if members else b'', bytes) else str(test.id)
        assert test_id_str in members or str(test.id).encode() in members

        # Cleanup
        client.delete('test:updated_ids')

    def test_apply_and_sync_updates_count(self):
        """apply 후 sync 태스크 실행 시 count가 증가하는지 확인"""
        # Given: 사용자와 test 생성
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # Given: 초기 count는 0
        assert test.registration_count == 0

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When: apply API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/apply/'
        data = {
            'amount': '45000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: apply 성공
        assert response.status_code == 201

        # When: sync 태스크 실행
        sync_registration_counts()

        # Then: count가 1로 증가해야 함
        test.refresh_from_db()
        assert test.registration_count == 1

        # Then: Redis Set이 비워져야 함
        members = client.smembers('test:updated_ids')
        assert len(members) == 0

    def test_multiple_applies_sync_correctly(self):
        """여러 사용자가 apply 후 sync 시 정확한 count"""
        # Given: 3명의 사용자와 test 생성
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When: 3명이 apply
        api_client = APIClient()

        for user in [user1, user2, user3]:
            api_client.force_authenticate(user=user)
            url = f'/api/tests/{test.id}/apply/'
            data = {
                'amount': '45000.00',
                'payment_method': 'card'
            }
            response = api_client.post(url, data, format='json')
            assert response.status_code == 201

        # When: sync 태스크 실행
        sync_registration_counts()

        # Then: count가 3이어야 함
        test.refresh_from_db()
        assert test.registration_count == 3


@pytest.mark.django_db(transaction=True)
class TestEnrollIntegrationWithRedis:
    """enroll 액션 Redis 통합 테스트"""

    def test_enroll_adds_course_id_to_redis(self):
        """enroll 성공 시 Redis Set에 course ID가 추가되는지 확인"""
        # Given: 사용자와 course 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('course:updated_ids')

        # When: enroll API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 201 Created 응답
        assert response.status_code == 201

        # Then: Redis Set에 course ID가 추가되어야 함
        members = client.smembers('course:updated_ids')
        course_id_str = str(course.id).encode() if isinstance(list(members)[0] if members else b'', bytes) else str(course.id)
        assert course_id_str in members or str(course.id).encode() in members

        # Cleanup
        client.delete('course:updated_ids')

    def test_enroll_and_sync_updates_count(self):
        """enroll 후 sync 태스크 실행 시 count가 증가하는지 확인"""
        # Given: 사용자와 course 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # Given: 초기 count는 0
        assert course.registration_count == 0

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('course:updated_ids')

        # When: enroll API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: enroll 성공
        assert response.status_code == 201

        # When: sync 태스크 실행
        sync_registration_counts()

        # Then: count가 1로 증가해야 함
        course.refresh_from_db()
        assert course.registration_count == 1


@pytest.mark.django_db(transaction=True)
class TestCancelIntegrationWithRedis:
    """cancel 액션 Redis 통합 테스트"""

    def test_cancel_test_adds_id_to_redis(self):
        """test payment 취소 시 Redis Set에 test ID가 추가되는지 확인"""
        # Given: 사용자, test, payment, registration 생성
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        payment = Payment.objects.create(
            user=user,
            amount=Decimal('45000.00'),
            payment_method='card',
            status='paid',
            payment_type='test',
            target=test
        )

        registration = TestRegistration.objects.create(
            user=user,
            test=test,
            status='applied'
        )

        # Given: 초기 count 설정
        test.registration_count = 1
        test.save()

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When: cancel API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 200 OK 응답
        assert response.status_code == 200

        # Then: Redis Set에 test ID가 추가되어야 함
        members = client.smembers('test:updated_ids')
        test_id_str = str(test.id).encode() if isinstance(list(members)[0] if members else b'', bytes) else str(test.id)
        assert test_id_str in members or str(test.id).encode() in members

        # Cleanup
        client.delete('test:updated_ids')

    def test_cancel_and_sync_decreases_count(self):
        """cancel 후 sync 시 count가 감소하는지 확인"""
        # Given: 2명의 사용자와 test, 둘 다 apply
        user1 = UserFactory()
        user2 = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        payment1 = Payment.objects.create(
            user=user1,
            amount=Decimal('45000.00'),
            payment_method='card',
            status='paid',
            payment_type='test',
            target=test
        )

        payment2 = Payment.objects.create(
            user=user2,
            amount=Decimal('45000.00'),
            payment_method='card',
            status='paid',
            payment_type='test',
            target=test
        )

        registration1 = TestRegistration.objects.create(
            user=user1,
            test=test,
            status='applied'
        )

        registration2 = TestRegistration.objects.create(
            user=user2,
            test=test,
            status='applied'
        )

        # Given: 초기 count 설정
        test.registration_count = 2
        test.save()

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When: user1이 cancel
        api_client = APIClient()
        api_client.force_authenticate(user=user1)
        url = f'/api/payments/{payment1.id}/cancel/'
        response = api_client.post(url)

        # Then: cancel 성공
        assert response.status_code == 200

        # When: sync 태스크 실행
        sync_registration_counts()

        # Then: count가 1로 감소해야 함
        test.refresh_from_db()
        assert test.registration_count == 1

    def test_cancel_course_adds_id_to_redis(self):
        """course payment 취소 시 Redis Set에 course ID가 추가되는지 확인"""
        # Given: 사용자, course, payment, registration 생성
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        payment = Payment.objects.create(
            user=user,
            amount=Decimal('50000.00'),
            payment_method='card',
            status='paid',
            payment_type='course',
            target=course
        )

        enrollment = CourseRegistration.objects.create(
            user=user,
            course=course,
            status='enrolled'
        )

        # Given: Redis Set 초기화
        client = get_redis_client()
        client.delete('course:updated_ids')

        # When: cancel API 호출
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/payments/{payment.id}/cancel/'
        response = api_client.post(url)

        # Then: 200 OK 응답
        assert response.status_code == 200

        # Then: Redis Set에 course ID가 추가되어야 함
        members = client.smembers('course:updated_ids')
        course_id_str = str(course.id).encode() if isinstance(list(members)[0] if members else b'', bytes) else str(course.id)
        assert course_id_str in members or str(course.id).encode() in members

        # Cleanup
        client.delete('course:updated_ids')


@pytest.mark.django_db(transaction=True)
class TestEndToEndCountAggregation:
    """전체 시나리오 통합 테스트"""

    def test_complete_flow_test_apply_sync_cancel_sync(self):
        """전체 플로우: apply → sync → cancel → sync"""
        # Given: 사용자와 test
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # Given: Redis 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')

        # Given: 초기 count는 0
        assert test.registration_count == 0

        # Step 1: apply
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/apply/'
        data = {
            'amount': '45000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201

        payment_id = response.data['payment_id']

        # Step 2: sync
        sync_registration_counts()

        # Then: count가 1이어야 함
        test.refresh_from_db()
        assert test.registration_count == 1

        # Step 3: cancel
        url = f'/api/payments/{payment_id}/cancel/'
        response = api_client.post(url)
        assert response.status_code == 200

        # Step 4: sync again
        sync_registration_counts()

        # Then: count가 0으로 돌아가야 함
        test.refresh_from_db()
        assert test.registration_count == 0

    def test_complete_flow_course_enroll_sync_cancel_sync(self):
        """전체 플로우: enroll → sync → cancel → sync"""
        # Given: 사용자와 course
        user = UserFactory()
        course = CourseFactory(price=Decimal('50000.00'))

        # Given: Redis 초기화
        client = get_redis_client()
        client.delete('course:updated_ids')

        # Given: 초기 count는 0
        assert course.registration_count == 0

        # Step 1: enroll
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/enroll/'
        data = {
            'amount': '50000.00',
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201

        payment_id = response.data['payment_id']

        # Step 2: sync
        sync_registration_counts()

        # Then: count가 1이어야 함
        course.refresh_from_db()
        assert course.registration_count == 1

        # Step 3: cancel
        url = f'/api/payments/{payment_id}/cancel/'
        response = api_client.post(url)
        assert response.status_code == 200

        # Step 4: sync again
        sync_registration_counts()

        # Then: count가 0으로 돌아가야 함
        course.refresh_from_db()
        assert course.registration_count == 0

    def test_mixed_test_and_course_operations(self):
        """test와 course 동시 작업 시나리오"""
        # Given: 사용자, test, course
        user1 = UserFactory()
        user2 = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))
        course = CourseFactory(price=Decimal('50000.00'))

        # Given: Redis 초기화
        client = get_redis_client()
        client.delete('test:updated_ids')
        client.delete('course:updated_ids')

        # When: user1이 test apply, user2가 course enroll
        api_client = APIClient()

        # Apply
        api_client.force_authenticate(user=user1)
        response = api_client.post(
            f'/api/tests/{test.id}/apply/',
            {'amount': '45000.00', 'payment_method': 'card'},
            format='json'
        )
        assert response.status_code == 201

        # Enroll
        api_client.force_authenticate(user=user2)
        response = api_client.post(
            f'/api/courses/{course.id}/enroll/',
            {'amount': '50000.00', 'payment_method': 'card'},
            format='json'
        )
        assert response.status_code == 201

        # When: sync
        sync_registration_counts()

        # Then: 둘 다 count가 1이어야 함
        test.refresh_from_db()
        course.refresh_from_db()

        assert test.registration_count == 1
        assert course.registration_count == 1
