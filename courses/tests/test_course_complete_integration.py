import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from courses.models import Course, CourseRegistration
from factories import UserFactory, CourseFactory, CourseRegistrationFactory


@pytest.mark.django_db(transaction=True)
class TestCourseCompleteIntegration:
    """수업 완료 처리 API 통합 테스트"""

    def test_complete_success_updates_status_and_timestamp(self, api_client):
        """정상적인 완료 처리 시 상태 및 타임스탬프 업데이트"""
        # Given: 사용자, 수업, CourseRegistration 생성 (status='enrolled')
        user = UserFactory()
        course = CourseFactory()
        enrollment = CourseRegistrationFactory(user=user, course=course, status='enrolled')

        # When: API Client 인증 및 완료 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200
        assert 'enrollment_id' in response.data
        assert 'completed_at' in response.data
        assert response.data['message'] == '수업이 완료되었습니다'

        # Then: DB에서 CourseRegistration 조회
        enrollment.refresh_from_db()
        assert enrollment.status == 'completed'
        assert enrollment.completed_at is not None

    def test_complete_success_preserves_other_fields(self, api_client):
        """완료 처리 시 다른 필드는 변경되지 않음"""
        # Given: CourseRegistration 생성
        user = UserFactory()
        course = CourseFactory()
        enrollment = CourseRegistrationFactory(user=user, course=course, status='enrolled')
        original_enrolled_at = enrollment.enrolled_at

        # When: 완료 처리 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 200 OK 응답 확인
        assert response.status_code == 200

        # Then: DB에서 CourseRegistration 조회
        enrollment.refresh_from_db()
        assert enrollment.enrolled_at == original_enrolled_at
        assert enrollment.user == user
        assert enrollment.course == course

    def test_complete_fails_when_unauthenticated(self, api_client):
        """인증되지 않은 요청은 거부"""
        # Given: 수업과 CourseRegistration 생성
        course = CourseFactory()
        enrollment = CourseRegistrationFactory(course=course)

        # When: 인증 없이 POST 요청
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 401 Unauthorized 응답 확인
        assert response.status_code == 401

    def test_complete_fails_when_no_registration(self, api_client):
        """수강 신청하지 않은 수업은 완료 불가"""
        # Given: 사용자와 수업 생성 (CourseRegistration 없음)
        user = UserFactory()
        course = CourseFactory()

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 404 Not Found 응답 확인
        assert response.status_code == 404
        assert '수강 신청 내역이 없습니다' in response.data['error']

    def test_complete_fails_when_already_completed(self, api_client):
        """이미 완료된 수업은 재완료 불가"""
        # Given: CourseRegistration 생성 (status='completed')
        user = UserFactory()
        course = CourseFactory()
        completed_at = timezone.now() - timedelta(days=1)
        enrollment = CourseRegistrationFactory(
            user=user,
            course=course,
            status='completed',
            completed_at=completed_at
        )

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '이미 완료된 수업입니다' in response.data['error']

        # Then: completed_at이 변경되지 않았는지 확인
        enrollment.refresh_from_db()
        assert enrollment.completed_at == completed_at

    def test_complete_fails_when_cancelled(self, api_client):
        """취소된 수강은 완료 불가"""
        # Given: CourseRegistration 생성 (status='cancelled')
        user = UserFactory()
        course = CourseFactory()
        enrollment = CourseRegistrationFactory(
            user=user,
            course=course,
            status='cancelled',
            cancelled_at=timezone.now()
        )

        # When: POST 요청
        api_client.force_authenticate(user=user)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 400 Bad Request 응답 확인
        assert response.status_code == 400
        assert '취소된 수업입니다' in response.data['error']

    def test_complete_fails_for_other_user_registration(self, api_client):
        """다른 사용자의 CourseRegistration은 완료 불가"""
        # Given: 사용자 A와 수업으로 CourseRegistration 생성
        user_a = UserFactory()
        user_b = UserFactory()
        course = CourseFactory()
        enrollment = CourseRegistrationFactory(user=user_a, course=course)

        # When: 사용자 B로 인증 및 완료 요청
        api_client.force_authenticate(user=user_b)
        url = f'/api/courses/{course.id}/complete/'
        response = api_client.post(url)

        # Then: 404 Not Found 응답 확인 (본인 것만 조회 가능)
        assert response.status_code == 404

    def test_complete_multiple_registrations_same_user(self, api_client):
        """같은 사용자가 여러 수업을 완료할 수 있음"""
        # Given: 사용자 1명, 수업 3개, CourseRegistration 3개 생성
        user = UserFactory()
        courses = [CourseFactory() for _ in range(3)]
        enrollments = [
            CourseRegistrationFactory(user=user, course=course)
            for course in courses
        ]

        # When: 각 수업에 대해 완료 요청
        api_client.force_authenticate(user=user)
        responses = []
        for course in courses:
            url = f'/api/courses/{course.id}/complete/'
            response = api_client.post(url)
            responses.append(response)

        # Then: 모든 요청이 200 OK 응답
        assert all(r.status_code == 200 for r in responses)

        # Then: 3개의 CourseRegistration이 모두 'completed' 상태인지 확인
        for enrollment in enrollments:
            enrollment.refresh_from_db()
            assert enrollment.status == 'completed'
            assert enrollment.completed_at is not None
