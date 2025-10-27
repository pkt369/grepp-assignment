import logging
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.filters import PaymentFilter
from tests.models import TestRegistration
from courses.models import CourseRegistration
from common.redis_lock import redis_lock
from common.redis_client import mark_test_updated, mark_course_updated

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=['Payments'],
        summary='결제 내역 목록 조회',
        description='본인의 결제 내역 목록을 조회합니다. 필터링과 검색을 지원합니다.',
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='결제 상태 필터 (paid, cancelled, refunded)',
                required=False,
            ),
            OpenApiParameter(
                name='payment_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='결제 유형 필터 (test, course)',
                required=False,
            ),
            OpenApiParameter(
                name='from',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='결제 시작 날짜 (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='to',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='결제 종료 날짜 (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='전체 텍스트 검색 (항목 제목 검색)',
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=['Payments'],
        summary='결제 내역 상세 조회',
        description='특정 결제 내역의 상세 정보를 조회합니다.',
    ),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    본인 결제 내역 조회 API ViewSet

    - 목록 조회: GET /api/me/payments/
    - 상세 조회: GET /api/me/payments/{id}/
    - 필터링: ?status=paid&payment_type=test
    - 날짜 범위: ?from=2025-01-01&to=2025-12-31
    - 전체 텍스트 검색: ?search=Django
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

    @extend_schema(
        tags=['Payments'],
        summary='결제 취소',
        description='결제를 취소합니다. 본인의 결제만 취소할 수 있으며, 관련 응시/수강 신청도 함께 취소됩니다.',
        request=None,
        responses={
            200: {'description': '결제 취소 성공'},
            400: {'description': '이미 취소된 결제'},
            401: {'description': '인증 필요'},
            403: {'description': '본인의 결제가 아님'},
            409: {'description': '동시 요청 충돌 (잠시 후 재시도)'},
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        결제 취소 API

        엔드포인트: POST /api/payments/{id}/cancel/

        응답 (200):
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
            logger.warning(
                f"Unauthorized payment cancellation attempt: "
                f"payment_id={payment.id}, payment_user={payment.user.id}, "
                f"request_user={request.user.id}"
            )
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
                        logger.warning(
                            f"Payment already cancelled: payment_id={payment.id}, "
                            f"status={payment.status}, user_id={request.user.id}"
                        )
                        return Response(
                            {"error": "이미 취소된 결제입니다"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # 6. Payment 상태 변경
                    payment.status = 'cancelled'
                    payment.cancelled_at = timezone.now()
                    payment.save()

                    # 7. 관련 Registration 삭제 (메인 비즈니스 로직)
                    if payment.payment_type == 'test' and payment.target:
                        # TestRegistration 삭제
                        test_id = payment.target.id
                        TestRegistration.objects.filter(
                            user=request.user,
                            test=payment.target
                        ).delete()

                        # Mark test as updated in Redis after transaction commits
                        transaction.on_commit(lambda: mark_test_updated(test_id))
                    elif payment.payment_type == 'course' and payment.target:
                        # CourseRegistration 삭제
                        course_id = payment.target.id
                        CourseRegistration.objects.filter(
                            user=request.user,
                            course=payment.target
                        ).delete()

                        # Mark course as updated in Redis after transaction commits
                        transaction.on_commit(lambda: mark_course_updated(course_id))

                logger.info(
                    f"Payment cancelled successfully: payment_id={payment.id}, "
                    f"user_id={request.user.id}, payment_type={payment.payment_type}"
                )

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
                logger.warning(
                    f"Lock acquisition failed for payment cancellation: "
                    f"payment_id={payment.id}, user_id={request.user.id}"
                )
                return Response(
                    {"error": "잠시 후 다시 시도해주세요"},
                    status=status.HTTP_409_CONFLICT
                )
            # 기타 예외
            logger.error(
                f"Payment cancellation failed: payment_id={payment.id}, "
                f"user_id={request.user.id}, error={str(e)}",
                exc_info=True
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Todo: 환불 구현
