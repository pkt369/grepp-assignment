"""
Integration tests for course list API - End-to-End scenarios
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework import status

from courses.models import Course, CourseRegistration
from accounts.models import User


@pytest.mark.django_db
class TestCourseListIntegration:
    """수업 목록 조회 통합 테스트 - 전체 시나리오"""

    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """테스트 환경 설정"""
        self.client = api_client
        self.now = timezone.now()

        # 여러 사용자 생성
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            username='user1',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='pass123'
        )
        self.user3 = User.objects.create_user(
            email='user3@example.com',
            username='user3',
            password='pass123'
        )

    def test_complete_user_journey_browsing_courses(self):
        """
        시나리오: 사용자가 수업 목록을 탐색하고 검색하는 전체 여정

        1. 로그인하지 않고 접근 시도 -> 401
        2. 로그인
        3. 전체 수업 목록 조회
        4. 수강 가능한 수업만 필터링
        5. 정렬 확인
        """
        # 수업 생성
        django_course = Course.objects.create(
            title='Django Advanced',
            description='Advanced Django concepts',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        python_course = Course.objects.create(
            title='Python Basics',
            description='Python fundamentals',
            price=Decimal('40000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )
        future_course = Course.objects.create(
            title='Django REST Framework',
            description='Building APIs with Django',
            price=Decimal('70000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=30)
        )

        # 인기도 설정
        CourseRegistration.objects.create(user=self.user2, course=django_course)
        CourseRegistration.objects.create(user=self.user3, course=django_course)
        CourseRegistration.objects.create(user=self.user2, course=python_course)

        # Update registration counts
        django_course.registration_count = 2
        django_course.save()
        python_course.registration_count = 1
        python_course.save()

        # 1. 인증 없이 접근 시도
        url = reverse('course-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. 로그인
        self.client.force_authenticate(user=self.user1)

        # 3. 전체 수업 목록 조회
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

        # 4. 수강 가능한 수업만 필터링
        response = self.client.get(url, {'status': 'available'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        ids = [r['id'] for r in response.data['results']]
        assert django_course.id in ids
        assert python_course.id in ids
        assert future_course.id not in ids

        # 5. 인기순 정렬
        response = self.client.get(url, {'sort': 'popular'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        # django_course(2명) > python_course(1명) > future_course(0명)
        assert results[0]['id'] == django_course.id
        assert results[0]['registration_count'] == 2

    def test_multi_user_registration_tracking(self):
        """
        시나리오: 여러 사용자의 수업 등록 추적

        1. user1이 수업 목록 조회 -> is_registered=False
        2. user1이 course에 등록
        3. user1이 다시 목록 조회 -> is_registered=True
        4. user2가 목록 조회 -> is_registered=False (user2는 등록 안 함)
        """
        course = Course.objects.create(
            title='Popular Course',
            description='Many people registered',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )

        url = reverse('course-list')

        # 1. user1 조회
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == course.id)
        assert not result['is_registered']
        assert result['registration_count'] == 0

        # 2. user1 등록
        CourseRegistration.objects.create(user=self.user1, course=course)
        course.registration_count = 1
        course.save()

        # 3. user1 다시 조회
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == course.id)
        assert result['is_registered']
        assert result['registration_count'] == 1

        # 4. user2 조회
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == course.id)
        assert not result['is_registered']  # user2는 등록 안 함
        assert result['registration_count'] == 1  # 하지만 총 등록자는 1명

    def test_pagination_works_correctly(self):
        """
        시나리오: 페이지네이션 동작 확인
        """
        # 25개의 수업 생성
        for i in range(25):
            Course.objects.create(
                title=f'Course {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now - timedelta(days=10),
                end_at=self.now + timedelta(days=10)
            )

        self.client.force_authenticate(user=self.user1)
        url = reverse('course-list')

        # 1페이지
        response = self.client.get(url, {'page': 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 25
        assert len(response.data['results']) == 20  # PAGE_SIZE
        assert response.data['next'] is not None
        assert response.data['previous'] is None

        # 2페이지
        response = self.client.get(url, {'page': 2})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5  # 나머지 5개
        assert response.data['next'] is None
        assert response.data['previous'] is not None

    def test_detail_view_integration(self):
        """
        시나리오: 수업 상세 조회

        1. 목록에서 수업 발견
        2. 상세 정보 조회
        3. 정확한 정보 확인
        """
        course = Course.objects.create(
            title='Django Advanced',
            description='Advanced Django concepts',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        CourseRegistration.objects.create(user=self.user1, course=course)
        CourseRegistration.objects.create(user=self.user2, course=course)
        course.registration_count = 2
        course.save()

        self.client.force_authenticate(user=self.user1)

        # 1. 목록에서 발견
        list_url = reverse('course-list')
        list_response = self.client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK

        # 2. 상세 조회
        detail_url = reverse('course-detail', kwargs={'pk': course.id})
        detail_response = self.client.get(detail_url)

        # 3. 정확한 정보 확인
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data['id'] == course.id
        assert detail_response.data['title'] == 'Django Advanced'
        assert detail_response.data['price'] == '60000.00'
        assert detail_response.data['is_registered']  # user1이 등록함
        assert detail_response.data['registration_count'] == 2

    def test_sorting_by_created_date(self):
        """
        시나리오: 최신순 정렬 확인
        """
        # 시간 간격을 두고 수업 생성
        course1 = Course.objects.create(
            title='Course 1',
            description='Description 1',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        course2 = Course.objects.create(
            title='Course 2',
            description='Description 2',
            price=Decimal('55000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        course3 = Course.objects.create(
            title='Course 3',
            description='Description 3',
            price=Decimal('60000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('course-list')

        # 최신순 정렬 (기본값)
        response = self.client.get(url, {'sort': 'created'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # 최신 순서대로 정렬되어야 함
        assert results[0]['id'] == course3.id
        assert results[1]['id'] == course2.id
        assert results[2]['id'] == course1.id

    def test_search_with_fts(self):
        """
        시나리오: Full-Text Search 기능 확인
        """
        # 다양한 주제의 수업 생성
        django_course = Course.objects.create(
            title='Django Advanced',
            description='Advanced Django concepts and patterns',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        python_course = Course.objects.create(
            title='Python Basics',
            description='Learn Python fundamentals',
            price=Decimal('40000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )
        react_course = Course.objects.create(
            title='React for Beginners',
            description='Building modern UIs with React',
            price=Decimal('55000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=20)
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('course-list')

        # Django 검색
        response = self.client.get(url, {'search': 'Django'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == django_course.id

        # Python 검색
        response = self.client.get(url, {'search': 'Python'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == python_course.id

        # React 검색
        response = self.client.get(url, {'search': 'React'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == react_course.id

        # OR 검색: Django OR Python
        response = self.client.get(url, {'search': 'Django OR Python'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_combined_filters_and_search(self):
        """
        시나리오: 검색 + 필터링 + 정렬 조합
        """
        # 과거 Django 수업
        Course.objects.create(
            title='Django Basics (Past)',
            description='Past Django course',
            price=Decimal('40000.00'),
            start_at=self.now - timedelta(days=30),
            end_at=self.now - timedelta(days=10)
        )

        # 현재 Django 수업 (인기)
        django_popular = Course.objects.create(
            title='Django Advanced',
            description='Advanced Django topics',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        CourseRegistration.objects.create(user=self.user1, course=django_popular)
        CourseRegistration.objects.create(user=self.user2, course=django_popular)
        django_popular.registration_count = 2
        django_popular.save()

        # 현재 Django 수업 (덜 인기)
        django_less = Course.objects.create(
            title='Django REST Framework',
            description='Building APIs',
            price=Decimal('55000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('course-list')

        # 복합 필터링: available + Django + popular
        response = self.client.get(url, {
            'status': 'available',
            'search': 'Django',
            'sort': 'popular'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2  # 현재 수강 가능한 Django 수업만

        results = response.data['results']
        # 인기순: django_popular(2명) > django_less(0명)
        assert results[0]['id'] == django_popular.id
        assert results[0]['registration_count'] == 2
        assert results[1]['id'] == django_less.id
        assert results[1]['registration_count'] == 0
