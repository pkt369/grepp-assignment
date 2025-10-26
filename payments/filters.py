import django_filters
from django.contrib.postgres.search import SearchQuery, SearchRank
from payments.models import Payment


class PaymentFilter(django_filters.FilterSet):
    """결제 내역 필터"""
    status = django_filters.CharFilter(
        field_name='status',
        help_text='결제 상태 (paid, cancelled)'
    )
    payment_type = django_filters.CharFilter(
        field_name='payment_type',
        help_text='결제 타입 (test, course)'
    )
    # 'from'은 ViewSet.get_queryset()에서 직접 처리
    to = django_filters.DateFilter(
        field_name='paid_at',
        lookup_expr='date__lte',
        help_text='결제 종료 날짜 (예: 2025-04-02)'
    )
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='전체 텍스트 검색 (항목 제목 기반)'
    )

    class Meta:
        model = Payment
        fields = ['status', 'payment_type', 'to', 'search']

    def filter_search(self, queryset, name, value):
        """전체 텍스트 검색 - Payment의 search_vector 활용"""
        if not value:
            return queryset

        # SearchQuery 생성
        search_query = SearchQuery(value, search_type='websearch', config='simple')

        # Payment의 search_vector로 직접 검색
        # Signal이 target의 title을 포함하여 자동 업데이트
        return queryset.filter(search_vector=search_query)
