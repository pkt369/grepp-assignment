"""
Tests for Celery tasks.
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from common.tasks import sync_registration_counts, sync_test_counts, sync_course_counts
from common.redis_client import get_redis_client
from tests.models import Test, TestRegistration
from courses.models import Course, CourseRegistration
from factories import UserFactory, TestFactory, CourseFactory


@pytest.mark.django_db(transaction=True)
class TestSyncTestCounts:
    """sync_test_counts 함수 테스트"""

    def test_sync_test_counts_updates_single_test(self):
        """단일 test의 카운트를 정확하게 업데이트하는지 확인"""
        # Given: test와 registrations 생성
        test = TestFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()

        TestRegistration.objects.create(user=user1, test=test, status='applied')
        TestRegistration.objects.create(user=user2, test=test, status='applied')
        TestRegistration.objects.create(user=user3, test=test, status='applied')

        # Given: Redis에 test ID 추가
        client = get_redis_client()
        client.sadd('test:updated_ids', test.id)

        # Given: 초기 count는 0
        assert test.registration_count == 0

        # When: sync_test_counts 실행
        sync_test_counts(client)

        # Then: count가 3으로 업데이트되어야 함
        test.refresh_from_db()
        assert test.registration_count == 3

        # Then: Redis Set이 비워져야 함
        members = client.smembers('test:updated_ids')
        assert len(members) == 0

    def test_sync_test_counts_updates_multiple_tests(self):
        """여러 test의 카운트를 동시에 업데이트"""
        # Given: 3개의 test와 각각 다른 수의 registrations
        test1 = TestFactory()
        test2 = TestFactory()
        test3 = TestFactory()

        # test1: 2개
        user1 = UserFactory()
        user2 = UserFactory()
        TestRegistration.objects.create(user=user1, test=test1, status='applied')
        TestRegistration.objects.create(user=user2, test=test1, status='applied')

        # test2: 1개
        user3 = UserFactory()
        TestRegistration.objects.create(user=user3, test=test2, status='applied')

        # test3: 0개 (등록 없음)

        # Given: Redis에 모든 test ID 추가
        client = get_redis_client()
        client.sadd('test:updated_ids', test1.id, test2.id, test3.id)

        # When: sync_test_counts 실행
        sync_test_counts(client)

        # Then: 각 test의 count가 정확해야 함
        test1.refresh_from_db()
        test2.refresh_from_db()
        test3.refresh_from_db()

        assert test1.registration_count == 2
        assert test2.registration_count == 1
        assert test3.registration_count == 0

        # Then: Redis Set이 비워져야 함
        members = client.smembers('test:updated_ids')
        assert len(members) == 0

    def test_sync_test_counts_handles_empty_set(self):
        """Redis Set이 비어있을 때 정상 처리"""
        # Given: 빈 Redis Set
        client = get_redis_client()
        client.delete('test:updated_ids')

        # When/Then: 에러 없이 실행되어야 함
        try:
            sync_test_counts(client)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")

    def test_sync_test_counts_updates_after_cancellation(self):
        """등록 취소 후 카운트가 감소하는지 확인"""
        # Given: test와 2개의 registrations
        test = TestFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        reg1 = TestRegistration.objects.create(user=user1, test=test, status='applied')
        reg2 = TestRegistration.objects.create(user=user2, test=test, status='applied')

        # Given: 초기 count 설정
        test.registration_count = 2
        test.save()

        # Given: 하나의 registration 삭제
        reg1.delete()

        # Given: Redis에 test ID 추가
        client = get_redis_client()
        client.sadd('test:updated_ids', test.id)

        # When: sync_test_counts 실행
        sync_test_counts(client)

        # Then: count가 1로 감소해야 함
        test.refresh_from_db()
        assert test.registration_count == 1

    @patch('common.tasks.logger')
    def test_sync_test_counts_logs_on_error(self, mock_logger):
        """에러 발생 시 로그를 남기는지 확인"""
        # Given: Redis 클라이언트가 에러를 발생시키도록 설정
        mock_client = MagicMock()
        mock_client.smembers.side_effect = Exception("Redis error")

        # When/Then: 에러가 발생하고 로깅되어야 함
        with pytest.raises(Exception):
            sync_test_counts(mock_client)

        mock_logger.error.assert_called_once()


@pytest.mark.django_db(transaction=True)
class TestSyncCourseCounts:
    """sync_course_counts 함수 테스트"""

    def test_sync_course_counts_updates_single_course(self):
        """단일 course의 카운트를 정확하게 업데이트하는지 확인"""
        # Given: course와 registrations 생성
        course = CourseFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        CourseRegistration.objects.create(user=user1, course=course, status='enrolled')
        CourseRegistration.objects.create(user=user2, course=course, status='enrolled')

        # Given: Redis에 course ID 추가
        client = get_redis_client()
        client.sadd('course:updated_ids', course.id)

        # Given: 초기 count는 0
        assert course.registration_count == 0

        # When: sync_course_counts 실행
        sync_course_counts(client)

        # Then: count가 2로 업데이트되어야 함
        course.refresh_from_db()
        assert course.registration_count == 2

        # Then: Redis Set이 비워져야 함
        members = client.smembers('course:updated_ids')
        assert len(members) == 0

    def test_sync_course_counts_updates_multiple_courses(self):
        """여러 course의 카운트를 동시에 업데이트"""
        # Given: 2개의 course와 각각 다른 수의 registrations
        course1 = CourseFactory()
        course2 = CourseFactory()

        # course1: 3개
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        CourseRegistration.objects.create(user=user1, course=course1, status='enrolled')
        CourseRegistration.objects.create(user=user2, course=course1, status='enrolled')
        CourseRegistration.objects.create(user=user3, course=course1, status='enrolled')

        # course2: 1개
        user4 = UserFactory()
        CourseRegistration.objects.create(user=user4, course=course2, status='enrolled')

        # Given: Redis에 모든 course ID 추가
        client = get_redis_client()
        client.sadd('course:updated_ids', course1.id, course2.id)

        # When: sync_course_counts 실행
        sync_course_counts(client)

        # Then: 각 course의 count가 정확해야 함
        course1.refresh_from_db()
        course2.refresh_from_db()

        assert course1.registration_count == 3
        assert course2.registration_count == 1

    def test_sync_course_counts_handles_empty_set(self):
        """Redis Set이 비어있을 때 정상 처리"""
        # Given: 빈 Redis Set
        client = get_redis_client()
        client.delete('course:updated_ids')

        # When/Then: 에러 없이 실행되어야 함
        try:
            sync_course_counts(client)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")


@pytest.mark.django_db(transaction=True)
class TestSyncRegistrationCounts:
    """sync_registration_counts 메인 태스크 테스트"""

    def test_sync_registration_counts_syncs_both_test_and_course(self):
        """test와 course 둘 다 동기화하는지 확인"""
        # Given: test와 course 각각 생성
        test = TestFactory()
        course = CourseFactory()

        user1 = UserFactory()
        user2 = UserFactory()

        TestRegistration.objects.create(user=user1, test=test, status='applied')
        CourseRegistration.objects.create(user=user2, course=course, status='enrolled')

        # Given: Redis에 ID 추가
        client = get_redis_client()
        client.sadd('test:updated_ids', test.id)
        client.sadd('course:updated_ids', course.id)

        # When: sync_registration_counts 실행
        sync_registration_counts()

        # Then: 둘 다 count가 업데이트되어야 함
        test.refresh_from_db()
        course.refresh_from_db()

        assert test.registration_count == 1
        assert course.registration_count == 1

        # Then: 둘 다 Redis Set이 비워져야 함
        assert len(client.smembers('test:updated_ids')) == 0
        assert len(client.smembers('course:updated_ids')) == 0

    @patch('common.tasks.get_redis_client')
    def test_sync_registration_counts_handles_redis_connection_failure(self, mock_get_client):
        """Redis 연결 실패 시 처리"""
        # Given: Redis 클라이언트가 None을 반환
        mock_get_client.return_value = None

        # When/Then: 에러 없이 종료되어야 함 (로그만 남김)
        try:
            sync_registration_counts()
        except Exception as e:
            # Redis 연결 실패는 태스크를 중단시키므로 에러가 발생하지 않아야 함
            pytest.fail(f"Should handle redis failure gracefully: {e}")

    def test_sync_registration_counts_idempotent(self):
        """같은 태스크를 여러 번 실행해도 결과가 동일한지 (멱등성)"""
        # Given: test와 registrations
        test = TestFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        TestRegistration.objects.create(user=user1, test=test, status='applied')
        TestRegistration.objects.create(user=user2, test=test, status='applied')

        # Given: Redis에 test ID 추가
        client = get_redis_client()
        client.sadd('test:updated_ids', test.id)

        # When: 첫 번째 실행
        sync_registration_counts()

        # Then: count가 2여야 함
        test.refresh_from_db()
        assert test.registration_count == 2

        # When: Redis에 다시 추가하고 두 번째 실행 (데이터는 그대로)
        client.sadd('test:updated_ids', test.id)
        sync_registration_counts()

        # Then: count가 여전히 2여야 함 (증가하지 않음)
        test.refresh_from_db()
        assert test.registration_count == 2
