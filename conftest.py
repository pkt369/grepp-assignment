import pytest
import redis
from django.conf import settings
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def disable_debug_toolbar(settings):
    """테스트 환경에서 debug_toolbar 비활성화"""
    settings.DEBUG = False
    # debug_toolbar를 INSTALLED_APPS와 MIDDLEWARE에서 제거
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS.remove('debug_toolbar')
    if 'debug_toolbar.middleware.DebugToolbarMiddleware' in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """테스트 데이터베이스 설정"""
    with django_db_blocker.unblock():
        # 마이그레이션은 pytest-django가 자동으로 처리
        pass


@pytest.fixture(autouse=True)
def redis_client():
    """
    Redis 연결 클라이언트 생성
    테스트 전후로 Redis DB flush (데이터 정리)
    """
    client = redis.Redis.from_url(
        settings.REDIS_LOCK_URL,
        decode_responses=True
    )

    # 테스트 전 정리
    client.flushdb()

    yield client

    # 테스트 후 정리
    client.flushdb()


@pytest.fixture
def api_client():
    """Django REST Framework의 APIClient 인스턴스 생성"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, db):
    """
    사용자를 생성하고 인증된 APIClient 반환

    Usage:
        def test_something(authenticated_client):
            user = authenticated_client.user
            response = authenticated_client.get('/api/endpoint/')
    """
    from accounts.models import User

    user = User.objects.create_user(
        email='testuser@example.com',
        username='testuser',
        password='testpass123'
    )

    api_client.force_authenticate(user=user)
    api_client.user = user  # 편의를 위해 user 속성 추가

    return api_client
