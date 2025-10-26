from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone

from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.filters import PaymentFilter
from tests.models import TestRegistration
from courses.models import CourseRegistration
from common.redis_lock import redis_lock


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    본인 결제 내역 조회 API ViewSet

    - 목록 조회: GET /api/me/payments/
    - 상세 조회: GET /api/me/payments/{id}/
    - 필터링: ?status=paid&payment_type=test
    - 날짜 범위: ?from=2025-01-01&to=2025-12-31
    - FTS 검색: ?search=Django
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = PaymentFilter

    def get_queryset(self):
        """
        본인의 결제만 조회
        - N+1 네트워크 조회 방지를 위해 select_related 사용 ( join 사용 )
        - 최신순 정렬
        """
        queryset = Payment.objects.filter(
            user=self.request.user
        ).select_related(
            'content_type'
        ).order_by('-paid_at')

        # 'from' 파라미터 처리 (Python 키워드이므로 직접 처리)
        from_date = self.request.query_params.get('from')
        if from_date:
            queryset = queryset.filter(paid_at__date__gte=from_date)

        return queryset


class PaymentCancelViewSet(viewsets.GenericViewSet):
    """
    결제 취소 API ViewSet

    - 결제 취소: POST /api/payments/{id}/cancel/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """모든 결제 조회 (권한은 cancel 액션에서 체크)"""
        return Payment.objects.all()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        결제 취소 API

        POST /api/payments/{id}/cancel/

        Response (200):
        {
            "message": "결제가 취소되었습니다",
            "payment_id": 1,
            "cancelled_at": "2025-10-26T12:34:56Z"
        }
        """
        # 1. 결제 객체 조회
        payment = self.get_object()

        # 2. 본인 결제인지 권한 확인
        if payment.user != request.user:
            return Response(
                {"error": "본인의 결제만 취소할 수 있습니다"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Redis Lock 획득
        lock_key = f"payment:cancel:{payment.id}"

        try:
            with redis_lock(lock_key, timeout=10, retry_times=3, retry_delay=0.1):
                # 4. 트랜잭션 시작 및 SELECT FOR UPDATE로 row-level lock 획득
                with transaction.atomic():
                    payment = Payment.objects.select_for_update().get(pk=payment.id)

                    # 5. 이미 취소/환불되었는지 확인
                    if payment.status in ['cancelled', 'refunded']:
                        return Response(
                            {"error": "이미 취소된 결제입니다"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # 6. Payment 상태 변경
                    payment.status = 'cancelled'
                    payment.cancelled_at = timezone.now()
                    payment.save()

                    # 7. 관련 Registration/Enrollment 삭제 (메인 비즈니스 로직)
                    if payment.payment_type == 'test' and payment.target:
                        # TestRegistration 삭제
                        TestRegistration.objects.filter(
                            user=request.user,
                            test=payment.target
                        ).delete()
                    elif payment.payment_type == 'course' and payment.target:
                        # CourseRegistration 삭제
                        CourseRegistration.objects.filter(
                            user=request.user,
                            course=payment.target
                        ).delete()

                # 8. 성공 응답
                return Response(
                    {
                        "message": "결제가 취소되었습니다",
                        "payment_id": payment.id,
                        "cancelled_at": payment.cancelled_at.isoformat()
                    },
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            # Lock 획득 실패인지 확인
            if "Failed to acquire lock" in str(e):
                return Response(
                    {"error": "잠시 후 다시 시도해주세요"},
                    status=status.HTTP_409_CONFLICT
                )
            # 기타 예외
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Todo: 환불 구현
