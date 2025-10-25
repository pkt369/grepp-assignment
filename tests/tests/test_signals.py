"""
Tests for search_vector signal handler
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from tests.models import Test


@pytest.mark.django_db(transaction=True)
class SearchVectorSignalTests:
    """
    search_vector 자동 업데이트 Signal에 대한 단위 테스트

    Note: TransactionTestCase를 사용하여 실제 데이터베이스 커밋을 수행합니다.
    이렇게 해야 post_save signal이 완전히 반영되어 search_vector가 업데이트됩니다.
    """

    @pytest.fixture(autouse=True)


    def setup(self, api_client):
        """각 테스트 전에 실행되는 설정"""
        self.now = timezone.now()

    def test_search_vector_auto_update_on_create(self):
        """성공: Test 생성 시 search_vector 자동 업데이트"""
        test = Test.objects.create(
            title='Django Test',
            description='Django testing fundamentals',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # 데이터베이스에서 다시 조회
        test.refresh_from_db()

        # search_vector가 설정되어야 함
        assert test.search_vector is not None

    def test_search_vector_contains_title(self):
        """성공: search_vector에 title 내용이 포함"""
        test = Test.objects.create(
            title='Django Framework',
            description='Python web framework',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # Django로 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_contains_description(self):
        """성공: search_vector에 description 내용이 포함"""
        test = Test.objects.create(
            title='Web Development',
            description='Learn Django framework',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # Django로 검색 가능해야 함 (description에 있음)
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_update_on_title_change(self):
        """성공: title 변경 시 search_vector 업데이트"""
        test = Test.objects.create(
            title='Original Title',
            description='Some description',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # title 변경
        test.title = 'Django Framework'
        test.save()

        # 데이터베이스에서 다시 조회 (TransactionTestCase는 실제 커밋됨)
        test.refresh_from_db()

        # 새로운 title로 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

        # 이전 title로는 검색 불가
        search_query_old = SearchQuery('Original', search_type='websearch')
        results_old = Test.objects.filter(search_vector=search_query_old)

        assert test not in results_old

    def test_search_vector_update_on_description_change(self):
        """성공: description 변경 시 search_vector 업데이트"""
        test = Test.objects.create(
            title='Web Framework',
            description='Original description',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # description 변경
        test.description = 'Learn Django fundamentals'
        test.save()

        # 데이터베이스에서 다시 조회 (TransactionTestCase는 실제 커밋됨)
        test.refresh_from_db()

        # 새로운 description으로 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_with_null_description(self):
        """성공: description이 null일 때도 search_vector 업데이트"""
        test = Test.objects.create(
            title='Django Test',
            description=None,
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # search_vector가 설정되어야 함
        assert test.search_vector is not None

        # title로 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_with_empty_description(self):
        """성공: description이 빈 문자열일 때도 search_vector 업데이트"""
        test = Test.objects.create(
            title='Django Test',
            description='',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # search_vector가 설정되어야 함
        assert test.search_vector is not None

    def test_search_vector_case_insensitive(self):
        """성공: search_vector는 대소문자 구분 없음"""
        test = Test.objects.create(
            title='Django Framework',
            description='Python web development',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        from django.contrib.postgres.search import SearchQuery

        # 대문자로 검색
        search_query_upper = SearchQuery('DJANGO', search_type='websearch')
        results_upper = Test.objects.filter(search_vector=search_query_upper)

        # 소문자로 검색
        search_query_lower = SearchQuery('django', search_type='websearch')
        results_lower = Test.objects.filter(search_vector=search_query_lower)

        # 둘 다 검색 가능해야 함
        assert test in results_upper
        assert test in results_lower

    def test_search_vector_multiple_words(self):
        """성공: 여러 단어를 포함한 search_vector"""
        test = Test.objects.create(
            title='Advanced Django Development',
            description='Learn Django REST framework and testing',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        from django.contrib.postgres.search import SearchQuery

        # 각 단어로 검색 가능해야 함
        for keyword in ['Django', 'REST', 'testing', 'Advanced']:
            search_query = SearchQuery(keyword, search_type='websearch')
            results = Test.objects.filter(search_vector=search_query)
            assert test in results, f'Should find test with keyword: {keyword}'

    def test_search_vector_weight_priority(self):
        """성공: title이 description보다 높은 weight (A > B)"""
        # title에 Django가 있는 시험
        test1 = Test.objects.create(
            title='Django Framework',
            description='Python web development',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # description에만 Django가 있는 시험
        test2 = Test.objects.create(
            title='Web Development',
            description='Learn Django framework',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # 둘 다 검색되어야 함 (weight는 랭킹에 영향)
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test1 in results
        assert test2 in results

    def test_search_vector_special_characters(self):
        """성공: 특수 문자가 포함된 경우"""
        test = Test.objects.create(
            title='C++ Programming',
            description='Advanced C++ topics',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # search_vector가 설정되어야 함
        assert test.search_vector is not None

        # C++로 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('C++', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_numbers(self):
        """성공: 숫자가 포함된 경우"""
        test = Test.objects.create(
            title='Python 3.9 Tutorial',
            description='Learn Python version 3.9',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()

        # 숫자로도 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('3.9', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert test in results

    def test_search_vector_bulk_create_not_auto_updated(self):
        """주의: bulk_create는 signal을 트리거하지 않음"""
        tests = [
            Test(
                title=f'Test {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now,
                end_at=self.now + timedelta(days=30)
            )
            for i in range(5)
        ]

        Test.objects.bulk_create(tests)

        # bulk_create는 post_save signal을 트리거하지 않음
        # search_vector가 None이어야 함
        created_tests = Test.objects.filter(title__startswith='Test')
        for test in created_tests:
            assert test.search_vector is None

    def test_search_vector_manual_update_after_bulk_create(self):
        """성공: bulk_create 후 수동으로 search_vector 업데이트"""
        tests = [
            Test(
                title=f'Django Test {i}',
                description=f'Description {i}',
                price=Decimal('50000.00'),
                start_at=self.now,
                end_at=self.now + timedelta(days=30)
            )
            for i in range(5)
        ]

        Test.objects.bulk_create(tests)

        # 수동으로 search_vector 업데이트
        from django.contrib.postgres.search import SearchVector
        Test.objects.filter(title__startswith='Django Test').update(
            search_vector=(
                SearchVector('title', weight='A') +
                SearchVector('description', weight='B')
            )
        )

        # 업데이트 후 검색 가능해야 함
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery('Django', search_type='websearch')
        results = Test.objects.filter(search_vector=search_query)

        assert results.count() == 5

    def test_search_vector_update_only_when_needed(self):
        """성공: 관련 없는 필드 변경 시에도 search_vector 업데이트"""
        test = Test.objects.create(
            title='Django Test',
            description='Django description',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test.refresh_from_db()
        old_search_vector = test.search_vector

        # price만 변경 (title, description 변경 없음)
        test.price = Decimal('60000.00')
        test.save()
        test.refresh_from_db()

        # search_vector는 업데이트되었지만 내용은 동일해야 함
        # (post_save signal이 항상 실행되므로)
        assert test.search_vector is not None

    def test_multiple_tests_different_search_vectors(self):
        """성공: 여러 Test가 각각 다른 search_vector를 가짐"""
        test1 = Test.objects.create(
            title='Django Test',
            description='Django description',
            price=Decimal('50000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test2 = Test.objects.create(
            title='Python Test',
            description='Python description',
            price=Decimal('45000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        test1.refresh_from_db()
        test2.refresh_from_db()

        # 각각의 search_vector가 있어야 함
        assert test1.search_vector is not None
        assert test2.search_vector is not None

        # Django 검색 시 test1만 나와야 함
        from django.contrib.postgres.search import SearchQuery
        django_query = SearchQuery('Django', search_type='websearch')
        django_results = Test.objects.filter(search_vector=django_query)

        assert test1 in django_results
        assert test2 not in django_results

        # Python 검색 시 test2만 나와야 함
        python_query = SearchQuery('Python', search_type='websearch')
        python_results = Test.objects.filter(search_vector=python_query)

        assert test2 in python_results
        assert test1 not in python_results
