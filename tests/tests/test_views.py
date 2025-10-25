"""
Tests for TestViewSet
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status

from tests.models import Test, TestRegistration
from accounts.models import User


class TestViewSetTests(TestCase):
    """TestViewSet에 대한 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        self.client = APIClient()

        # 사용자 생성
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )

        self.now = timezone.now()

        # 여러 시험 생성
        self.test1 = Test.objects.create(
            title='Django Test 1',
            description='Django fundamentals',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        self.test2 = Test.objects.create(
            title='Python Test 2',
            description='Python basics',
            price=Decimal('45000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=20)
        )
        self.test3 = Test.objects.create(
            title='JavaScript Test 3',
            description='JavaScript advanced',
            price=Decimal('55000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=30)
        )

        # test1에 여러 사용자 등록 (인기도 테스트용)
        TestRegistration.objects.create(user=self.user, test=self.test1)
        TestRegistration.objects.create(user=self.other_user, test=self.test1)

        # test2에 한 사용자만 등록
        TestRegistration.objects.create(user=self.user, test=self.test2)

    def test_list_tests_unauthenticated(self):
        """실패: 인증되지 않은 요청은 401 반환"""
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_tests_authenticated(self):
        """성공: 인증된 요청은 200 반환"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_tests_contains_all_tests(self):
        """성공: 모든 시험이 목록에 포함"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

    def test_list_tests_response_structure(self):
        """성공: 응답 구조 검증"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 페이지네이션 필드 확인
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

        # 첫 번째 결과의 필드 확인
        result = response.data['results'][0]
        expected_fields = [
            'id', 'title', 'description', 'price',
            'start_at', 'end_at', 'created_at',
            'is_registered', 'registration_count'
        ]
        for field in expected_fields:
            self.assertIn(field, result)

    def test_list_tests_is_registered_field(self):
        """성공: is_registered 필드가 올바르게 설정"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 결과를 id로 매핑
        results = {r['id']: r for r in response.data['results']}

        # test1과 test2는 등록됨, test3은 등록 안 됨
        self.assertTrue(results[self.test1.id]['is_registered'])
        self.assertTrue(results[self.test2.id]['is_registered'])
        self.assertFalse(results[self.test3.id]['is_registered'])

    def test_list_tests_registration_count_field(self):
        """성공: registration_count 필드가 올바르게 설정"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = {r['id']: r for r in response.data['results']}

        # test1: 2명, test2: 1명, test3: 0명
        self.assertEqual(results[self.test1.id]['registration_count'], 2)
        self.assertEqual(results[self.test2.id]['registration_count'], 1)
        self.assertEqual(results[self.test3.id]['registration_count'], 0)

    def test_list_tests_different_user_sees_different_is_registered(self):
        """성공: 다른 사용자는 다른 is_registered 값을 봄"""
        # user의 경우
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response1 = self.client.get(url)

        results1 = {r['id']: r for r in response1.data['results']}

        # other_user의 경우
        self.client.force_authenticate(user=self.other_user)
        response2 = self.client.get(url)

        results2 = {r['id']: r for r in response2.data['results']}

        # test1: 둘 다 등록
        self.assertTrue(results1[self.test1.id]['is_registered'])
        self.assertTrue(results2[self.test1.id]['is_registered'])

        # test2: user만 등록
        self.assertTrue(results1[self.test2.id]['is_registered'])
        self.assertFalse(results2[self.test2.id]['is_registered'])

    def test_retrieve_test_unauthenticated(self):
        """실패: 인증되지 않은 상세 조회는 401 반환"""
        url = reverse('test-detail', kwargs={'pk': self.test1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_test_authenticated(self):
        """성공: 인증된 상세 조회는 200 반환"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-detail', kwargs={'pk': self.test1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.test1.id)
        self.assertEqual(response.data['title'], self.test1.title)

    def test_retrieve_test_not_found(self):
        """실패: 존재하지 않는 시험 조회는 404 반환"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-detail', kwargs={'pk': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_test_not_allowed(self):
        """실패: ReadOnlyViewSet이므로 생성 불가"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        data = {
            'title': 'New Test',
            'description': 'New description',
            'price': '60000.00',
            'start_at': self.now,
            'end_at': self.now + timedelta(days=30)
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_test_not_allowed(self):
        """실패: ReadOnlyViewSet이므로 수정 불가"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-detail', kwargs={'pk': self.test1.id})
        data = {'title': 'Updated Title'}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_test_not_allowed(self):
        """실패: ReadOnlyViewSet이므로 삭제 불가"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-detail', kwargs={'pk': self.test1.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_by_status_available(self):
        """성공: status=available 필터링"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'status': 'available'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # test1과 test2만 현재 응시 가능 (test3은 미래)
        self.assertEqual(response.data['count'], 2)

        ids = [r['id'] for r in response.data['results']]
        self.assertIn(self.test1.id, ids)
        self.assertIn(self.test2.id, ids)
        self.assertNotIn(self.test3.id, ids)

    def test_filter_by_status_invalid(self):
        """성공: 유효하지 않은 status 값은 필터링 안 함"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'status': 'invalid'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 모든 시험 반환
        self.assertEqual(response.data['count'], 3)

    def test_search_by_keyword(self):
        """성공: search 파라미터로 검색"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'search': 'Django'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Django가 포함된 시험만
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.test1.id)

    def test_search_multiple_keywords(self):
        """성공: 여러 키워드로 검색"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'search': 'Django OR Python'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Django 또는 Python이 포함된 시험
        self.assertEqual(response.data['count'], 2)

    def test_sort_by_created(self):
        """성공: sort=created로 최신순 정렬"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'sort': 'created'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']

        # 최신순이므로 test3 -> test2 -> test1
        self.assertEqual(results[0]['id'], self.test3.id)
        self.assertEqual(results[1]['id'], self.test2.id)
        self.assertEqual(results[2]['id'], self.test1.id)

    def test_sort_by_popular(self):
        """성공: sort=popular로 인기순 정렬"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'sort': 'popular'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']

        # 인기순이므로 test1(2명) -> test2(1명) -> test3(0명)
        self.assertEqual(results[0]['id'], self.test1.id)
        self.assertEqual(results[0]['registration_count'], 2)
        self.assertEqual(results[1]['id'], self.test2.id)
        self.assertEqual(results[1]['registration_count'], 1)
        self.assertEqual(results[2]['id'], self.test3.id)
        self.assertEqual(results[2]['registration_count'], 0)

    def test_default_sort_is_created(self):
        """성공: 기본 정렬은 최신순"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']

        # 기본은 최신순
        self.assertEqual(results[0]['id'], self.test3.id)

    def test_combined_filter_and_search(self):
        """성공: 필터와 검색 동시 사용"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {
            'status': 'available',
            'search': 'Django'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # available이면서 Django가 포함된 시험
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.test1.id)

    def test_combined_filter_and_sort(self):
        """성공: 필터와 정렬 동시 사용"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {
            'status': 'available',
            'sort': 'popular'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']

        # available이면서 인기순
        self.assertEqual(results[0]['id'], self.test1.id)
        self.assertEqual(results[1]['id'], self.test2.id)

    def test_combined_all_parameters(self):
        """성공: 필터, 검색, 정렬 모두 동시 사용"""
        # 추가 테스트 데이터 생성
        test4 = Test.objects.create(
            title='Django Advanced',
            description='Advanced Django topics',
            price=Decimal('65000.00'),
            start_at=self.now - timedelta(days=7),
            end_at=self.now + timedelta(days=15)
        )
        TestRegistration.objects.create(user=self.user, test=test4)
        TestRegistration.objects.create(user=self.other_user, test=test4)

        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {
            'status': 'available',
            'search': 'Django',
            'sort': 'popular'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # available + Django + popular 순
        self.assertEqual(response.data['count'], 2)

    def test_pagination_first_page(self):
        """성공: 첫 페이지 조회"""
        # 많은 시험 생성 (페이지네이션 테스트용)
        for i in range(25):
            Test.objects.create(
                title=f'Test {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now,
                end_at=self.now + timedelta(days=30)
            )

        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'page': 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # PAGE_SIZE가 20이면 20개 반환
        self.assertEqual(len(response.data['results']), 20)
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_pagination_second_page(self):
        """성공: 두 번째 페이지 조회"""
        for i in range(25):
            Test.objects.create(
                title=f'Test {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now,
                end_at=self.now + timedelta(days=30)
            )

        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'page': 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 두 번째 페이지는 나머지 8개 (3 + 25 = 28개 총)
        self.assertEqual(len(response.data['results']), 8)
        self.assertIsNone(response.data['next'])
        self.assertIsNotNone(response.data['previous'])

    def test_pagination_invalid_page(self):
        """실패: 유효하지 않은 페이지 번호"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'page': 999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_count_optimization(self):
        """성공: 쿼리 개수 최적화 확인 (N+1 문제 해결)"""
        # 더 많은 시험과 등록 생성
        for i in range(10):
            test = Test.objects.create(
                title=f'Test {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now,
                end_at=self.now + timedelta(days=30)
            )
            TestRegistration.objects.create(user=self.user, test=test)

        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')

        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with override_settings(DEBUG=True):
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 쿼리 개수가 5개 이하여야 함 (N+1 문제 없음)
        # 1. User 조회, 2. Test 목록 조회 (annotate 포함), 3. Count 쿼리 등
        self.assertLessEqual(len(queries), 5)

    def test_empty_queryset(self):
        """성공: 시험이 없을 때"""
        Test.objects.all().delete()

        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

    def test_filter_no_results(self):
        """성공: 필터 결과가 없을 때"""
        self.client.force_authenticate(user=self.user)
        url = reverse('test-list')
        response = self.client.get(url, {'search': 'NonExistentKeyword'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)
