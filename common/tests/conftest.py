"""
Pytest fixtures for common app tests.
"""
import pytest
from django.conf import settings
from common.redis_client import get_redis_client


@pytest.fixture(autouse=True)
def disable_debug_toolbar(settings):
    """테스트 환경에서 debug_toolbar 비활성화"""
    settings.DEBUG = False
    # debug_toolbar를 INSTALLED_APPS와 MIDDLEWARE에서 제거
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS.remove('debug_toolbar')
    if 'debug_toolbar.middleware.DebugToolbarMiddleware' in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')


@pytest.fixture(scope='function', autouse=True)
def clean_redis():
    """각 테스트 전후로 Redis Set을 정리"""
    client = get_redis_client()
    if client:
        # 테스트 전 정리
        client.flushdb()  # 전체 DB를 정리 (테스트 DB 전용)

    yield

    # 테스트 후 정리
    if client:
        client.flushdb()
