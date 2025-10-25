import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from tests.models import Test, TestRegistration
from tests.factories import UserFactory, TestFactory, TestRegistrationFactory


@pytest.mark.django_db(transaction=True)
class TestCompleteIntegration:
    """시험 완료 처리 API 통합 테스트"""

    def test_complete_success_updates_status_and_timestamp(self, api_client):
        """정상적인 완료 처리 시 상태 및 타임스탬프 업데이트"""
        # Given: 사용자, 시험, TestRegistration 생성 (status='applied')
        user = UserFactory()
        test = TestFactory()
        registration = TestRegistrationFactory(user=user, test=test, status='applied')

        # When: API Client 인증 및 완료 요청
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200
        assert 'registration_id' in response.data
        assert 'completed_at' in response.data
        assert response.data['message'] == '시험이 완료되었습니다'

        # Then: DB에서 TestRegistration 조회
        registration.refresh_from_db()
        assert registration.status == 'completed'
        assert registration.completed_at is not None

    def test_complete_success_preserves_other_fields(self, api_client):
        """완료 처리 시 다른 필드는 변경되지 않음"""
        # Given: TestRegistration 생성
        user = UserFactory()
        test = TestFactory()
        registration = TestRegistrationFactory(user=user, test=test, status='applied')
        original_applied_at = registration.applied_at

        # When: 완료 처리 요청
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: DB에서 TestRegistration 조회
        registration.refresh_from_db()
        assert registration.applied_at == original_applied_at
        assert registration.user == user
        assert registration.test == test

    def test_complete_fails_when_unauthenticated(self, api_client):
        """인증되지 않은 요청은 거부"""
        # Given: 시험과 TestRegistration 생성
        test = TestFactory()
        registration = TestRegistrationFactory(test=test)

        # When: 인증 없이 POST 요청
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 401 Unauthorized 응답 확인
        assert response.status_code == 401

    def test_complete_fails_when_no_registration(self, api_client):
        """응시 신청하지 않은 시험은 완료 불가"""
        # Given: 사용자와 시험 생성 (TestRegistration 없음)
        user = UserFactory()
        test = TestFactory()

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 404 Not Found 응답 확인
        assert response.status_code == 404
        assert '응시 신청 내역이 없습니다' in response.data['error']

    def test_complete_fails_when_already_completed(self, api_client):
        """이미 완료된 시험은 재완료 불가"""
        # Given: TestRegistration 생성 (status='completed')
        user = UserFactory()
        test = TestFactory()
        completed_at = timezone.now() - timedelta(days=1)
        registration = TestRegistrationFactory(
            user=user,
            test=test,
            status='completed',
            completed_at=completed_at
        )

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '이미 완료된 시험입니다' in response.data['error']

        # Then: completed_at이 변경되지 않았는지 확인
        registration.refresh_from_db()
        assert registration.completed_at == completed_at

    def test_complete_fails_when_cancelled(self, api_client):
        """취소된 응시는 완료 불가"""
        # Given: TestRegistration 생성 (status='cancelled')
        user = UserFactory()
        test = TestFactory()
        registration = TestRegistrationFactory(
            user=user,
            test=test,
            status='cancelled',
            cancelled_at=timezone.now()
        )

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '취소된 시험입니다' in response.data['error']

    def test_complete_fails_for_other_user_registration(self, api_client):
        """다른 사용자의 TestRegistration은 완료 불가"""
        # Given: 사용자 A와 시험으로 TestRegistration 생성
        user_a = UserFactory()
        user_b = UserFactory()
        test = TestFactory()
        registration = TestRegistrationFactory(user=user_a, test=test)

        # When: 사용자 B로 인증 및 완료 요청
        api_client.force_authenticate(user=user_b)
        url = f'/api/tests/{test.id}/complete/'
        response = api_client.post(url)

        # Then: 404 Not Found 응답 확인 (본인 것만 조회 가능)
        assert response.status_code == 404

    def test_complete_multiple_registrations_same_user(self, api_client):
        """같은 사용자가 여러 시험을 완료할 수 있음"""
        # Given: 사용자 1명, 시험 3개, TestRegistration 3개 생성
        user = UserFactory()
        tests = [TestFactory() for _ in range(3)]
        registrations = [
            TestRegistrationFactory(user=user, test=test)
            for test in tests
        ]

        # When: 각 시험에 대해 완료 요청
        api_client.force_authenticate(user=user)
        responses = []
        for test in tests:
            url = f'/api/tests/{test.id}/complete/'
            response = api_client.post(url)
            responses.append(response)

        # Then: 모든 요청이 200 OK 응답
        assert all(r.status_code == 200 for r in responses)

        # Then: 3개의 TestRegistration이 모두 'completed' 상태인지 확인
        for registration in registrations:
            registration.refresh_from_db()
            assert registration.status == 'completed'
            assert registration.completed_at is not None
