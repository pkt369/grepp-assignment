from django_filters import rest_framework as filters
from django.utils import timezone
from django.contrib.postgres.search import SearchQuery
from .models import Test


class TestFilter(filters.FilterSet):
    """
    시험 필터

    필터:
    - status=available: 현재 응시 가능한 시험만 조회 (start_at <= now <= end_at)
    - search: Full-Text Search로 title, description에서 검색
    """
    status = filters.CharFilter(method='filter_status')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = Test
        fields = ['status', 'search']

    def filter_status(self, queryset, name, value):
        """
        status 파라미터에 따라 필터링

        - available: 현재 응시 가능한 시험 (start_at <= now <= end_at)
        - 그 외: 필터링 안 함
        """
        if value == 'available':
            now = timezone.now()
            return queryset.filter(
                start_at__lte=now,
                end_at__gte=now
            )
        return queryset

    def filter_search(self, queryset, name, value):
        """
        search 파라미터로 Full-Text Search 수행

        - SearchQuery를 사용하여 검색어 변환
        - search_type='websearch': 공백으로 단어 구분 (예: "Django Python")
        - search_vector 필드에서 검색 (GIN 인덱스 사용)
        """
        if value:
            search_query = SearchQuery(value, search_type='websearch', config='simple')
            return queryset.filter(search_vector=search_query)
        return queryset
