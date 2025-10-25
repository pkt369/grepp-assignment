from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Exists, OuterRef
from .models import Test, TestRegistration
from .serializers import TestSerializer
from .filters import TestFilter


class TestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    시험 API ViewSet

    - 목록 조회: GET /tests/
    - 상세 조회: GET /tests/{id}/
    - 필터링: ?status=available
    - 정렬: ?sort=created (최신순) 또는 ?sort=popular (인기순)
    """
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TestFilter

    def get_queryset(self):
        """
        쿼리셋 최적화

        - annotate로 registration_count 계산
        - annotate로 is_registered_flag 계산 (Exists 사용)
        - 정렬 처리
        """
        queryset = Test.objects.all()

        # 현재 사용자
        user = self.request.user

        # 1. registration_count 추가 (응시자 수)
        queryset = queryset.annotate(
            registration_count=Count('registrations')
        )

        # 2. is_registered_flag 추가 ( 현재 사용자의 응시 여부 )
        # Exists를 사용하여 네트워크 N + 1 호출 제거
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_registered_flag=Exists(
                    TestRegistration.objects.filter(
                        test=OuterRef('pk'),
                        user=user
                    )
                )
            )

        # 3. 정렬 처리
        sort = self.request.query_params.get('sort', 'created')

        if sort == 'popular':
            # 인기순: 응시자 많은 순
            queryset = queryset.order_by('-registration_count', '-created_at')
        elif sort == 'created':
            # 최신순: 생성일 기준
            queryset = queryset.order_by('-created_at')
        else:
            # 기본 정렬
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_serializer_context(self):
        """
        Serializer에 request 전달
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
