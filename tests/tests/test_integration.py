"""
Integration tests for the tests app - End-to-End scenarios
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status

from tests.models import Test, TestRegistration
from accounts.models import User


@pytest.mark.django_db
class TestListIntegrationTests:
    """시험 목록 조회 통합 테스트 - 전체 시나리오"""

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

    def test_complete_user_journey_browsing_tests(self):
        """
        시나리오: 사용자가 시험 목록을 탐색하고 검색하는 전체 여정

        1. 로그인하지 않고 접근 시도 -> 401
        2. 로그인
        3. 전체 시험 목록 조회
        4. 응시 가능한 시험만 필터링
        5. Django 검색
        6. 인기순 정렬
        """
        # 시험 생성
        django_test = Test.objects.create(
            title='Django Advanced',
            description='Advanced Django concepts',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        python_test = Test.objects.create(
            title='Python Basics',
            description='Python fundamentals',
            price=Decimal('40000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )
        future_test = Test.objects.create(
            title='Django REST Framework',
            description='Building APIs with Django',
            price=Decimal('70000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=30)
        )

        # 인기도 설정
        TestRegistration.objects.create(user=self.user2, test=django_test)
        TestRegistration.objects.create(user=self.user3, test=django_test)
        TestRegistration.objects.create(user=self.user2, test=python_test)

        # Update registration counts
        django_test.registration_count = 2
        django_test.save()
        python_test.registration_count = 1
        python_test.save()

        # 1. 인증 없이 접근 시도
        url = reverse('test-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. 로그인
        self.client.force_authenticate(user=self.user1)

        # 3. 전체 시험 목록 조회
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

        # 4. 응시 가능한 시험만 필터링
        response = self.client.get(url, {'status': 'available'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        ids = [r['id'] for r in response.data['results']]
        assert django_test.id in ids
        assert python_test.id in ids
        assert future_test.id not in ids

        # 5. Django 검색
        response = self.client.get(url, {'search': 'Django'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2  # Django Advanced와 Django REST

        # 6. 인기순 정렬
        response = self.client.get(url, {'sort': 'popular'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        # django_test(2명) > python_test(1명) > future_test(0명)
        assert results[0]['id'] == django_test.id
        assert results[0]['registration_count'] == 2

    def test_multi_user_registration_tracking(self):
        """
        시나리오: 여러 사용자의 시험 등록 추적

        1. user1이 시험 목록 조회 -> is_registered=False
        2. user1이 test1에 등록
        3. user1이 다시 목록 조회 -> is_registered=True
        4. user2가 목록 조회 -> is_registered=False (user2는 등록 안 함)
        5. user2가 test1에 등록
        6. 모든 사용자가 목록 조회 -> registration_count 증가 확인
        """
        test = Test.objects.create(
            title='Popular Test',
            description='Many people registered',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )

        url = reverse('test-list')

        # 1. user1 조회
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == test.id)
        assert not result['is_registered']
        assert result['registration_count'] == 0

        # 2. user1 등록
        TestRegistration.objects.create(user=self.user1, test=test)
        test.registration_count = 1
        test.save()

        # 3. user1 다시 조회
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == test.id)
        assert result['is_registered']
        assert result['registration_count'] == 1

        # 4. user2 조회
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == test.id)
        assert not result['is_registered']  # user2는 등록 안 함
        assert result['registration_count'] == 1  # 하지만 총 등록자는 1명

        # 5. user2 등록
        TestRegistration.objects.create(user=self.user2, test=test)
        test.registration_count = 2
        test.save()

        # 6. 모든 사용자가 조회
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == test.id)
        assert result['is_registered']
        assert result['registration_count'] == 2

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)
        result = next(r for r in response.data['results'] if r['id'] == test.id)
        assert result['is_registered']
        assert result['registration_count'] == 2

    def test_complex_filtering_scenario(self):
        """
        시나리오: 복잡한 필터링 조합

        1. 많은 시험 생성 (과거/현재/미래, 다양한 주제)
        2. 응시 가능 + Django 검색 + 인기순 정렬
        3. 페이지네이션으로 결과 탐색
        """
        # 과거 시험
        Test.objects.create(
            title='Django Basics (Past)',
            description='Finished course',
            price=Decimal('40000.00'),
            start_at=self.now - timedelta(days=30),
            end_at=self.now - timedelta(days=10)
        )

        # 현재 응시 가능한 Django 시험 (인기)
        django_popular = Test.objects.create(
            title='Django Advanced',
            description='Advanced Django topics',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        TestRegistration.objects.create(user=self.user1, test=django_popular)
        TestRegistration.objects.create(user=self.user2, test=django_popular)
        TestRegistration.objects.create(user=self.user3, test=django_popular)
        django_popular.registration_count = 3
        django_popular.save()

        # 현재 응시 가능한 Django 시험 (덜 인기)
        django_less_popular = Test.objects.create(
            title='Django REST Framework',
            description='Building APIs',
            price=Decimal('55000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )
        TestRegistration.objects.create(user=self.user1, test=django_less_popular)
        django_less_popular.registration_count = 1
        django_less_popular.save()

        # 현재 응시 가능한 Python 시험
        Test.objects.create(
            title='Python Basics',
            description='Python fundamentals',
            price=Decimal('45000.00'),
            start_at=self.now - timedelta(days=7),
            end_at=self.now + timedelta(days=14)
        )

        # 미래 Django 시험
        Test.objects.create(
            title='Django Testing',
            description='Testing Django applications',
            price=Decimal('50000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=30)
        )

        # 복합 필터링: available + Django + popular
        self.client.force_authenticate(user=self.user1)
        url = reverse('test-list')
        response = self.client.get(url, {
            'status': 'available',
            'search': 'Django',
            'sort': 'popular'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        results = response.data['results']
        # 인기순: django_popular(3명) > django_less_popular(1명)
        assert results[0]['id'] == django_popular.id
        assert results[0]['registration_count'] == 3
        assert results[1]['id'] == django_less_popular.id
        assert results[1]['registration_count'] == 1

    def test_search_with_multiple_keywords(self):
        """
        시나리오: 다양한 키워드 조합으로 검색

        1. 단일 키워드 검색
        2. 여러 키워드 AND 검색
        3. 여러 키워드 OR 검색
        """
        # 다양한 시험 생성
        Test.objects.create(
            title='Django REST Framework',
            description='Building REST APIs with Django',
            price=Decimal('60000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        Test.objects.create(
            title='Python Web Development',
            description='Building web applications',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        Test.objects.create(
            title='JavaScript Basics',
            description='JavaScript fundamentals',
            price=Decimal('45000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('test-list')

        # 1. 단일 키워드: Django
        response = self.client.get(url, {'search': 'Django'})
        assert response.data['count'] == 1

        # 2. AND 검색: Django REST (둘 다 포함)
        response = self.client.get(url, {'search': 'Django REST'})
        assert response.data['count'] == 1

        # 3. OR 검색: Django OR Python
        response = self.client.get(url, {'search': 'Django OR Python'})
        assert response.data['count'] == 2

        # 4. OR 검색: Django OR Python OR JavaScript
        response = self.client.get(url, {'search': 'Django OR Python OR JavaScript'})
        assert response.data['count'] == 3

    def test_pagination_with_filters(self):
        """
        시나리오: 필터링된 결과의 페이지네이션

        1. 많은 시험 생성
        2. 필터 적용
        3. 페이지별로 조회
        """
        # 30개의 Django 시험 생성
        for i in range(30):
            Test.objects.create(
                title=f'Django Test {i}',
                description=f'Django description {i}',
                price=Decimal('50000.00'),
                start_at=self.now - timedelta(days=10),
                end_at=self.now + timedelta(days=10)
            )

        # 10개의 Python 시험 생성
        for i in range(10):
            Test.objects.create(
                title=f'Python Test {i}',
                description=f'Python description {i}',
                price=Decimal('45000.00'),
                start_at=self.now - timedelta(days=5),
                end_at=self.now + timedelta(days=15)
            )

        self.client.force_authenticate(user=self.user1)
        url = reverse('test-list')

        # Django 검색 (30개 결과)
        response = self.client.get(url, {'search': 'Django', 'page': 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 30
        assert len(response.data['results']) == 20  # PAGE_SIZE
        assert response.data['next'] is not None
        assert response.data['previous'] is None

        # 2페이지
        response = self.client.get(url, {'search': 'Django', 'page': 2})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 10  # 나머지 10개
        assert response.data['next'] is None
        assert response.data['previous'] is not None

    def test_detail_view_integration(self):
        """
        시나리오: 시험 상세 조회

        1. 목록에서 시험 발견
        2. 상세 정보 조회
        3. 정확한 정보 확인
        """
        test = Test.objects.create(
            title='Django Advanced',
            description='Advanced Django concepts',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        TestRegistration.objects.create(user=self.user1, test=test)
        TestRegistration.objects.create(user=self.user2, test=test)
        test.registration_count = 2
        test.save()

        self.client.force_authenticate(user=self.user1)

        # 1. 목록에서 발견
        list_url = reverse('test-list')
        list_response = self.client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK

        # 2. 상세 조회
        detail_url = reverse('test-detail', kwargs={'pk': test.id})
        detail_response = self.client.get(detail_url)

        # 3. 정확한 정보 확인
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data['id'] == test.id
        assert detail_response.data['title'] == 'Django Advanced'
        assert detail_response.data['price'] == '60000.00'
        assert detail_response.data['is_registered']  # user1이 등록함
        assert detail_response.data['registration_count'] == 2

    def test_performance_with_large_dataset(self):
        """
        시나리오: 대용량 데이터셋에서의 성능

        1. 100개 이상의 시험 생성
        2. 다양한 필터 조합
        3. 쿼리 개수가 일정 수준 이하인지 확인
        """
        # 100개의 시험 생성
        tests = []
        for i in range(100):
            test = Test.objects.create(
                title=f'Test {i} - {"Django" if i % 2 == 0 else "Python"}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now - timedelta(days=10),
                end_at=self.now + timedelta(days=10)
            )
            tests.append(test)

            # 일부 시험에 등록
            if i % 3 == 0:
                TestRegistration.objects.create(user=self.user1, test=test)
            if i % 5 == 0:
                TestRegistration.objects.create(user=self.user2, test=test)

        self.client.force_authenticate(user=self.user1)
        url = reverse('test-list')

        # 쿼리 개수 측정
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with override_settings(DEBUG=True):
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url, {
                    'status': 'available',
                    'search': 'Django',
                    'sort': 'popular'
                })

        assert response.status_code == status.HTTP_200_OK

        # N+1 문제 없이 일정 수준 이하의 쿼리
        assert len(queries) <= 5

    def test_concurrent_user_views(self):
        """
        시나리오: 여러 사용자가 동시에 조회

        1. 각 사용자가 다른 시험에 등록
        2. 각 사용자가 목록 조회
        3. 각자 다른 is_registered 값을 확인
        """
        test1 = Test.objects.create(
            title='Test 1',
            description='Description 1',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        test2 = Test.objects.create(
            title='Test 2',
            description='Description 2',
            price=Decimal('55000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        test3 = Test.objects.create(
            title='Test 3',
            description='Description 3',
            price=Decimal('60000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # 각 사용자가 다른 시험에 등록
        TestRegistration.objects.create(user=self.user1, test=test1)
        TestRegistration.objects.create(user=self.user2, test=test2)
        TestRegistration.objects.create(user=self.user3, test=test3)

        url = reverse('test-list')

        # user1 조회
        self.client.force_authenticate(user=self.user1)
        response1 = self.client.get(url)
        results1 = {r['id']: r for r in response1.data['results']}

        # user2 조회
        self.client.force_authenticate(user=self.user2)
        response2 = self.client.get(url)
        results2 = {r['id']: r for r in response2.data['results']}

        # user3 조회
        self.client.force_authenticate(user=self.user3)
        response3 = self.client.get(url)
        results3 = {r['id']: r for r in response3.data['results']}

        # 각 사용자는 자신이 등록한 시험만 is_registered=True
        assert results1[test1.id]['is_registered']
        assert not results1[test2.id]['is_registered']
        assert not results1[test3.id]['is_registered']

        assert not results2[test1.id]['is_registered']
        assert results2[test2.id]['is_registered']
        assert not results2[test3.id]['is_registered']

        assert not results3[test1.id]['is_registered']
        assert not results3[test2.id]['is_registered']
        assert results3[test3.id]['is_registered']
