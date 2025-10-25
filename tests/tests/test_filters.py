"""
Tests for TestFilter
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from tests.models import Test
from tests.filters import TestFilter


class TestFilterTests(TestCase):
    """TestFilter에 대한 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        self.now = timezone.now()

        # 현재 응시 가능한 시험
        self.available_test1 = Test.objects.create(
            title='Django Available',
            description='Django testing fundamentals',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )
        self.available_test2 = Test.objects.create(
            title='Python Available',
            description='Python basics',
            price=Decimal('45000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=20)
        )

        # 아직 시작하지 않은 시험
        self.future_test = Test.objects.create(
            title='JavaScript Future',
            description='JavaScript advanced',
            price=Decimal('55000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=30)
        )

        # 이미 종료된 시험
        self.past_test = Test.objects.create(
            title='React Past',
            description='React fundamentals',
            price=Decimal('60000.00'),
            start_at=self.now - timedelta(days=30),
            end_at=self.now - timedelta(days=10)
        )

    def test_filter_status_available(self):
        """성공: status=available 필터링"""
        filter_set = TestFilter(
            data={'status': 'available'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        self.assertEqual(filtered_qs.count(), 2)

        # 현재 응시 가능한 시험만 포함
        self.assertIn(self.available_test1, filtered_qs)
        self.assertIn(self.available_test2, filtered_qs)

        # 미래 및 과거 시험은 제외
        self.assertNotIn(self.future_test, filtered_qs)
        self.assertNotIn(self.past_test, filtered_qs)

    def test_filter_status_no_value(self):
        """성공: status 필터가 없으면 모든 시험 반환"""
        filter_set = TestFilter(
            data={},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        self.assertEqual(filtered_qs.count(), 4)

    def test_filter_status_invalid_value(self):
        """성공: 유효하지 않은 status 값은 필터링 안 함"""
        filter_set = TestFilter(
            data={'status': 'invalid_status'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # 모든 시험 반환 (필터링 안 됨)
        self.assertEqual(filtered_qs.count(), 4)

    def test_filter_status_at_boundary_start(self):
        """엣지 케이스: 정확히 시작 시간에 있는 시험"""
        boundary_test = Test.objects.create(
            title='Boundary Start Test',
            description='At exact start time',
            price=Decimal('40000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=10)
        )

        filter_set = TestFilter(
            data={'status': 'available'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # boundary_test도 포함되어야 함
        self.assertIn(boundary_test, filtered_qs)

    def test_filter_status_at_boundary_end(self):
        """엣지 케이스: 정확히 종료 시간에 있는 시험"""
        # 약간 미래 시간을 end_at로 설정 (테스트 실행 시간 고려)
        end_time = timezone.now() + timedelta(seconds=1)
        boundary_test = Test.objects.create(
            title='Boundary End Test',
            description='At exact end time',
            price=Decimal('40000.00'),
            start_at=end_time - timedelta(days=10),
            end_at=end_time
        )

        filter_set = TestFilter(
            data={'status': 'available'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # boundary_test도 포함되어야 함
        self.assertIn(boundary_test, filtered_qs)

    def test_search_filter_single_word(self):
        """성공: 단일 단어 검색"""
        filter_set = TestFilter(
            data={'search': 'Django'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # Django가 포함된 시험만 반환
        self.assertIn(self.available_test1, filtered_qs)
        self.assertNotIn(self.available_test2, filtered_qs)
        self.assertNotIn(self.future_test, filtered_qs)
        self.assertNotIn(self.past_test, filtered_qs)

    def test_search_filter_multiple_words(self):
        """성공: 여러 단어 검색 (AND 로직)"""
        # "Django testing" 검색 (둘 다 포함)
        filter_set = TestFilter(
            data={'search': 'Django testing'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # Django와 testing이 모두 포함된 시험만
        self.assertIn(self.available_test1, filtered_qs)

    def test_search_filter_or_logic(self):
        """성공: OR 로직 검색"""
        filter_set = TestFilter(
            data={'search': 'Django OR Python'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # Django 또는 Python이 포함된 시험
        self.assertIn(self.available_test1, filtered_qs)
        self.assertIn(self.available_test2, filtered_qs)

    def test_search_filter_case_insensitive(self):
        """성공: 대소문자 구분 없이 검색"""
        filter_set = TestFilter(
            data={'search': 'django'},  # 소문자
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # 대소문자 관계없이 매칭
        self.assertIn(self.available_test1, filtered_qs)

    def test_search_filter_no_results(self):
        """성공: 검색 결과가 없는 경우"""
        filter_set = TestFilter(
            data={'search': 'NonExistentKeyword'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        self.assertEqual(filtered_qs.count(), 0)

    def test_search_filter_empty_string(self):
        """성공: 빈 검색어는 필터링 안 함"""
        filter_set = TestFilter(
            data={'search': ''},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # 모든 시험 반환
        self.assertEqual(filtered_qs.count(), 4)

    def test_search_filter_no_search_param(self):
        """성공: search 파라미터가 없으면 필터링 안 함"""
        filter_set = TestFilter(
            data={},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # 모든 시험 반환
        self.assertEqual(filtered_qs.count(), 4)

    def test_search_in_description(self):
        """성공: description에서도 검색"""
        filter_set = TestFilter(
            data={'search': 'fundamentals'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # description에 fundamentals가 포함된 시험들
        self.assertIn(self.available_test1, filtered_qs)
        self.assertIn(self.past_test, filtered_qs)

    def test_combined_filters_status_and_search(self):
        """성공: status와 search 필터 동시 사용"""
        filter_set = TestFilter(
            data={'status': 'available', 'search': 'Django'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # 현재 응시 가능하고 Django가 포함된 시험만
        self.assertEqual(filtered_qs.count(), 1)
        self.assertIn(self.available_test1, filtered_qs)

    def test_combined_filters_no_overlap(self):
        """실패: 조건을 만족하는 결과가 없는 경우"""
        filter_set = TestFilter(
            data={'status': 'available', 'search': 'React'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        # React는 과거 시험이므로 available 필터에 걸림
        self.assertEqual(filtered_qs.count(), 0)

    def test_filter_preserves_queryset_order(self):
        """성공: 필터링 후에도 원래 쿼리셋 순서 유지"""
        # created_at 역순으로 정렬된 쿼리셋
        ordered_qs = Test.objects.all().order_by('-created_at')

        filter_set = TestFilter(
            data={'status': 'available'},
            queryset=ordered_qs
        )

        filtered_qs = filter_set.qs
        # 순서가 유지되는지 확인
        results = list(filtered_qs)
        self.assertEqual(results[0].created_at >= results[1].created_at, True)

    def test_filter_with_special_characters_in_search(self):
        """성공: 특수 문자가 포함된 검색어"""
        # 특수 문자가 포함된 시험 생성
        special_test = Test.objects.create(
            title='C++ Programming',
            description='C++ advanced topics',
            price=Decimal('70000.00'),
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )

        filter_set = TestFilter(
            data={'search': 'C++'},
            queryset=Test.objects.all()
        )

        filtered_qs = filter_set.qs
        self.assertIn(special_test, filtered_qs)

    def test_filter_meta_fields(self):
        """성공: FilterSet Meta 설정 확인"""
        filter_set = TestFilter()

        # Meta 설정이 올바른지 확인
        self.assertEqual(filter_set._meta.model, Test)
        self.assertIn('status', filter_set._meta.fields)
        self.assertIn('search', filter_set._meta.fields)
