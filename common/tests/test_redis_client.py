"""
Tests for Redis client utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from common.redis_client import (
    get_redis_client,
    mark_test_updated,
    mark_course_updated
)


@pytest.mark.django_db
class TestGetRedisClient:
    """get_redis_client 함수 테스트"""

    def test_get_redis_client_returns_connection(self):
        """Redis 연결을 정상적으로 반환하는지 확인"""
        # When: Redis 클라이언트를 가져옴
        client = get_redis_client()

        # Then: 클라이언트가 None이 아니어야 함
        assert client is not None

        # Then: ping이 성공해야 함
        assert client.ping() is True

    @patch('common.redis_client.get_redis_connection')
    def test_get_redis_client_handles_connection_error(self, mock_get_connection):
        """Redis 연결 실패 시 None을 반환하는지 확인"""
        # Given: Redis 연결이 실패하도록 설정
        mock_get_connection.side_effect = Exception("Connection failed")

        # When: Redis 클라이언트를 가져옴
        client = get_redis_client()

        # Then: None을 반환해야 함
        assert client is None


@pytest.mark.django_db
class TestMarkTestUpdated:
    """mark_test_updated 함수 테스트"""

    def test_mark_test_updated_adds_id_to_redis(self):
        """test ID가 Redis Set에 추가되는지 확인"""
        # Given: Redis 클라이언트
        client = get_redis_client()
        test_id = 12345

        # When: test ID를 마킹
        mark_test_updated(test_id)

        # Then: Redis Set에 ID가 추가되어야 함
        members = client.smembers('test:updated_ids')
        assert b'12345' in members or '12345' in members

    def test_mark_test_updated_handles_duplicates(self):
        """같은 ID를 여러 번 추가해도 Set은 중복을 제거해야 함"""
        # Given: Redis 클라이언트
        client = get_redis_client()
        test_id = 99999

        # When: 같은 ID를 3번 추가
        mark_test_updated(test_id)
        mark_test_updated(test_id)
        mark_test_updated(test_id)

        # Then: Set에는 하나만 있어야 함
        members = client.smembers('test:updated_ids')
        assert len(members) == 1

    def test_mark_test_updated_handles_multiple_ids(self):
        """여러 다른 ID를 추가할 수 있는지 확인"""
        # Given: Redis 클라이언트
        client = get_redis_client()

        # When: 여러 ID 추가
        mark_test_updated(1)
        mark_test_updated(2)
        mark_test_updated(3)

        # Then: 모든 ID가 Set에 있어야 함
        members = client.smembers('test:updated_ids')
        assert len(members) == 3

    @patch('common.redis_client.get_redis_client')
    def test_mark_test_updated_handles_redis_failure(self, mock_get_client):
        """Redis 연결 실패 시 에러를 무시하고 계속 진행"""
        # Given: Redis 클라이언트가 None을 반환
        mock_get_client.return_value = None

        # When/Then: 에러 없이 실행되어야 함
        try:
            mark_test_updated(123)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")

    @patch('common.redis_client.get_redis_client')
    def test_mark_test_updated_handles_sadd_error(self, mock_get_client):
        """SADD 실행 중 에러 발생 시 무시"""
        # Given: Redis 클라이언트의 sadd가 에러 발생
        mock_client = MagicMock()
        mock_client.sadd.side_effect = Exception("SADD failed")
        mock_get_client.return_value = mock_client

        # When/Then: 에러 없이 실행되어야 함
        try:
            mark_test_updated(123)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")


@pytest.mark.django_db
class TestMarkCourseUpdated:
    """mark_course_updated 함수 테스트"""

    def test_mark_course_updated_adds_id_to_redis(self):
        """course ID가 Redis Set에 추가되는지 확인"""
        # Given: Redis 클라이언트
        client = get_redis_client()
        course_id = 67890

        # When: course ID를 마킹
        mark_course_updated(course_id)

        # Then: Redis Set에 ID가 추가되어야 함
        members = client.smembers('course:updated_ids')
        assert b'67890' in members or '67890' in members

    def test_mark_course_updated_handles_duplicates(self):
        """같은 ID를 여러 번 추가해도 Set은 중복을 제거해야 함"""
        # Given: Redis 클라이언트
        client = get_redis_client()
        course_id = 88888

        # When: 같은 ID를 3번 추가
        mark_course_updated(course_id)
        mark_course_updated(course_id)
        mark_course_updated(course_id)

        # Then: Set에는 하나만 있어야 함
        members = client.smembers('course:updated_ids')
        assert len(members) == 1

    @patch('common.redis_client.get_redis_client')
    def test_mark_course_updated_handles_redis_failure(self, mock_get_client):
        """Redis 연결 실패 시 에러를 무시하고 계속 진행"""
        # Given: Redis 클라이언트가 None을 반환
        mock_get_client.return_value = None

        # When/Then: 에러 없이 실행되어야 함
        try:
            mark_course_updated(456)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")
