import pytest
import time
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.test import APIClient

from tests.models import Test, TestRegistration
from tests.factories import UserFactory, TestFactory
from payments.models import Payment
from common.redis_lock import redis_client


@pytest.mark.django_db(transaction=True)
class TestRedisLockIntegration:
    """Redis Lock 통합 테스트"""

    def test_lock_prevents_race_condition_in_apply(self):
        """Lock이 race condition을 방지하는지 검증"""
        # Given: 사용자와 시험 생성
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # When: 동시 요청 10개 전송
        def make_request():
            client = APIClient()
            client.force_authenticate(user=user)
            url = f'/api/tests/{test.id}/apply/'
            data = {
                'amount': '45000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # Then: 성공 응답(201)은 정확히 1개만 확인
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 1

        # Then: 중복 생성이 방지됨을 확인
        assert Payment.objects.filter(user=user, object_id=test.id).count() == 1
        assert TestRegistration.objects.filter(user=user, test=test).count() == 1

    def test_lock_released_after_exception(self, api_client):
        """예외 발생 시에도 Lock이 해제되는지 검증"""
        # Given: 시험 생성 (가격 불일치를 유발할 데이터)
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # When: POST 요청 (금액 불일치로 400 에러 발생)
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/apply/'
        data = {
            'amount': '50000.00',  # 가격 불일치
            'payment_method': 'card'
        }
        response = api_client.post(url, data, format='json')

        # Then: 400 에러 확인
        assert response.status_code == 400

        # Then: Redis에서 Lock 키 조회
        lock_key = f"lock:payment:user:{user.id}:test:{test.id}"
        lock_exists = redis_client.exists(lock_key)

        # Then: Lock이 해제되었는지 확인 (존재하지 않음)
        assert lock_exists == 0

    def test_lock_auto_expires(self):
        """Lock이 timeout 후 자동 만료되는지 검증"""
        # Given: Lock 키 생성
        lock_key = "lock:test:auto_expire"

        # When: Lock 설정 (timeout=1초)
        redis_client.set(lock_key, "test_value", ex=1)

        # Then: Lock이 존재하는지 확인
        assert redis_client.exists(lock_key) == 1

        # When: 1.5초 대기
        time.sleep(1.5)

        # Then: Lock이 만료되었는지 확인
        assert redis_client.exists(lock_key) == 0

    def test_lock_allows_different_users_different_locks(self):
        """서로 다른 사용자는 서로 다른 Lock을 사용하는지 검증"""
        # Given: 시험 1개, 사용자 5명 생성
        test = TestFactory(price=Decimal('45000.00'))
        users = [UserFactory() for _ in range(5)]

        # When: 각 사용자가 동시에 신청
        def make_request(user):
            client = APIClient()
            client.force_authenticate(user=user)
            url = f'/api/tests/{test.id}/apply/'
            data = {
                'amount': '45000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, user) for user in users]
            results = [future.result() for future in as_completed(futures)]

        # Then: 모든 요청이 성공
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 5

        # Then: 각 사용자별로 등록 생성 확인
        assert TestRegistration.objects.filter(test=test).count() == 5

    def test_lock_prevents_concurrent_same_user_same_test(self):
        """같은 사용자가 같은 시험에 동시 신청 시 1개만 성공"""
        # Given: 사용자와 시험 생성
        user = UserFactory()
        test = TestFactory(price=Decimal('45000.00'))

        # When: 같은 사용자로 동시 요청 20개
        def make_request():
            client = APIClient()
            client.force_authenticate(user=user)
            url = f'/api/tests/{test.id}/apply/'
            data = {
                'amount': '45000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]

        # Then: 성공은 1개만
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 1

        # Then: DB에 1개만 생성
        assert TestRegistration.objects.filter(user=user, test=test).count() == 1
        assert Payment.objects.filter(user=user, object_id=test.id).count() == 1

    def test_lock_allows_same_user_different_tests(self):
        """같은 사용자가 다른 시험에 동시 신청 시 모두 성공"""
        # Given: 사용자 1명, 시험 5개 생성
        user = UserFactory()
        tests = [TestFactory(price=Decimal('45000.00')) for _ in range(5)]

        # When: 각 시험에 동시 신청
        def make_request(test):
            client = APIClient()
            client.force_authenticate(user=user)
            url = f'/api/tests/{test.id}/apply/'
            data = {
                'amount': '45000.00',
                'payment_method': 'card'
            }
            return client.post(url, data, format='json')

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, test) for test in tests]
            results = [future.result() for future in as_completed(futures)]

        # Then: 모든 요청이 성공
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 5

        # Then: 각 시험별로 등록 생성 확인
        assert TestRegistration.objects.filter(user=user).count() == 5
