import logging
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Exists, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Course, CourseRegistration
from .serializers import CourseSerializer, CourseEnrollSerializer
from .filters import CourseFilter
from payments.strategies import PaymentStrategyFactory
from common.redis_lock import redis_lock
from common.redis_client import mark_course_updated

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=['Courses'],
        summary='수업 목록 조회',
        description='수업 목록을 조회합니다. 필터링과 정렬을 지원합니다.',
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='상태 필터 (available: 현재 수강 가능한 수업만)',
                required=False,
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='전체 텍스트 검색 (제목 및 설명 검색)',
                required=False,
            ),
            OpenApiParameter(
                name='sort',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='정렬 방식 (created: 최신순, popular: 인기순)',
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=['Courses'],
        summary='수업 상세 조회',
        description='특정 수업의 상세 정보를 조회합니다.',
    ),
)
class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    수업 API ViewSet

    - 목록 조회: GET /api/courses/
    - 상세 조회: GET /api/courses/{id}/
    - 필터링: ?status=available
    - 정렬: ?sort=created (최신순) 또는 ?sort=popular (인기순)
    """
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CourseFilter

    def get_queryset(self):
        """
        쿼리셋 최적화

        - registration_count 필드 사용 (사전 집계)
        - annotate로 is_registered_flag 계산 (Exists 사용)
        - 정렬 처리
        """
        queryset = Course.objects.all()

        user = self.request.user

        sort = self.request.query_params.get('sort', 'created')

        # is_registered_flag 추가 ( 현재 사용자의 수강 여부 )
        # Exists를 사용하여 네트워크 N + 1 호출 제거
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_registered_flag=Exists(
                    CourseRegistration.objects.filter(
                        course=OuterRef('pk'),
                        user=user
                    )
                )
            )

        # 정렬 처리
        if sort == 'popular':
            # 인기순: 사전 집계된 registration_count 사용
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

    @extend_schema(
        tags=['Courses'],
        summary='수업 수강 신청',
        description='수업 수강을 신청합니다. 결제 정보를 함께 제공해야 합니다.',
        request=CourseEnrollSerializer,
        responses={
            201: {'description': '수강 신청 성공'},
            400: {'description': '잘못된 요청 (중복 신청, 금액 불일치, 기간 만료 등)'},
            401: {'description': '인증 필요'},
            409: {'description': '동시 요청 충돌 (잠시 후 재시도)'},
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        """
        수업 수강 신청 API

        엔드포인트: POST /api/courses/{id}/enroll/

        요청 본문:
        {
            "amount": "50000.00",
            "payment_method": "card"
        }

        응답 (201):
        {
            "message": "수업 수강 신청이 완료되었습니다",
            "payment_id": 1,
            "enrollment_id": 1
        }
        """
        # 1. 요청 데이터 검증
        serializer = CourseEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 수업 객체 및 사용자 정보 가져오기
        course = self.get_object()
        user = request.user
        validated_data = serializer.validated_data

        # 3. Redis Lock 획득
        lock_key = f"enrollment:user:{user.id}:course:{course.id}"

        try:
            with redis_lock(lock_key, timeout=10, retry_times=3, retry_delay=0.1):
                # 4. 비즈니스 로직 검증
                # 4-1. 중복 수강 체크
                if CourseRegistration.objects.filter(user=user, course=course).exists():
                    logger.warning(
                        f"Duplicate course enrollment attempt: user_id={user.id}, course_id={course.id}"
                    )
                    return Response(
                        {"error": "이미 수강 신청한 수업입니다"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 4-2. 수강 가능 기간 검증
                if not course.is_available():
                    logger.warning(
                        f"Course not available: user_id={user.id}, course_id={course.id}, "
                        f"start={course.start_date}, end={course.end_date}"
                    )
                    return Response(
                        {"error": "현재 수강 가능한 기간이 아닙니다"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 4-3. 금액 일치 검증 -> 할인 정책이 있을 경우 삭제 필요
                if validated_data['amount'] != course.price:
                    logger.warning(
                        f"Price mismatch: user_id={user.id}, course_id={course.id}, "
                        f"expected={course.price}, received={validated_data['amount']}"
                    )
                    return Response(
                        {"error": "결제 금액이 수업 가격과 일치하지 않습니다"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 5. Strategy 패턴을 사용한 결제 처리
                try:
                    # 5-1. 결제 전략 가져오기
                    payment_strategy = PaymentStrategyFactory.get_strategy(
                        validated_data['payment_method']
                    )

                    # 5-2. 결제 수단별 검증
                    is_valid, error_message = payment_strategy.validate_payment(
                        amount=validated_data['amount']
                    )
                    if not is_valid:
                        return Response(
                            {"error": error_message},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # 5-3. 트랜잭션으로 결제 처리 및 등록 생성
                    with transaction.atomic():
                        payment = payment_strategy.process_payment(
                            user=user,
                            amount=validated_data['amount'],
                            payment_type='course',
                            target_model=Course,
                            target_id=course.id
                        )

                        # CourseRegistration 생성
                        enrollment = CourseRegistration.objects.create(
                            user=user,
                            course=course,
                            status='enrolled'
                        )

                        # Mark course as updated in Redis after transaction commits
                        transaction.on_commit(lambda: mark_course_updated(course.id))

                    # 5-4. 거래 메타데이터 가져오기
                    metadata = payment_strategy.get_transaction_metadata(
                        amount=validated_data['amount']
                    )

                    # 6. 성공 응답
                    logger.info(
                        f"Course enrollment success: user_id={user.id}, course_id={course.id}, "
                        f"payment_id={payment.id}, enrollment_id={enrollment.id}, "
                        f"payment_method={payment_strategy.get_payment_method()}"
                    )
                    return Response(
                        {
                            "message": "수업 수강 신청이 완료되었습니다",
                            "payment_id": payment.id,
                            "enrollment_id": enrollment.id,
                            "payment_method": payment_strategy.get_payment_method(),
                            "transaction_metadata": metadata
                        },
                        status=status.HTTP_201_CREATED
                    )

                except ValueError as e:
                    # 지원하지 않는 결제 수단
                    logger.error(
                        f"Invalid payment method: user_id={user.id}, course_id={course.id}, error={str(e)}",
                        exc_info=True
                    )
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except Exception as e:
            # Lock 획득 실패인지 확인
            if "Failed to acquire lock" in str(e):
                logger.warning(
                    f"Lock acquisition failed: user_id={user.id}, course_id={course.id}"
                )
                return Response(
                    {"error": "잠시 후 다시 시도해주세요"},
                    status=status.HTTP_409_CONFLICT
                )
            # 기타 예외
            logger.error(
                f"Course enrollment failed: user_id={user.id}, course_id={course.id}, error={str(e)}",
                exc_info=True
            )
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Courses'],
        summary='수업 완료 처리',
        description='수업을 완료 처리합니다. 이미 수강 신청한 수업만 완료할 수 있습니다.',
        request=None,
        responses={
            200: {'description': '수업 완료 성공'},
            400: {'description': '이미 완료되었거나 취소된 수업'},
            401: {'description': '인증 필요'},
            404: {'description': '수강 신청 내역이 없음'},
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """
        수업 완료 처리 API

        엔드포인트: POST /api/courses/{id}/complete/

        응답 (200):
        {
            "message": "수업이 완료되었습니다",
            "enrollment_id": 1,
            "completed_at": "2025-10-25T12:34:56Z"
        }
        """
        # 1. 수업 객체 및 사용자 정보 가져오기
        course = self.get_object()
        user = request.user

        # 2. 수강 내역 조회
        enrollment = CourseRegistration.objects.filter(
            user=user,
            course=course
        ).first()

        if not enrollment:
            logger.warning(
                f"Course completion failed - no enrollment: user_id={user.id}, course_id={course.id}"
            )
            return Response(
                {"error": "수강 신청 내역이 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. 상태 검증
        if enrollment.status == 'completed':
            logger.warning(
                f"Course already completed: user_id={user.id}, course_id={course.id}, "
                f"enrollment_id={enrollment.id}"
            )
            return Response(
                {"error": "이미 완료된 수업입니다"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if enrollment.status == 'cancelled':
            logger.warning(
                f"Course completion failed - cancelled: user_id={user.id}, course_id={course.id}, "
                f"enrollment_id={enrollment.id}"
            )
            return Response(
                {"error": "취소된 수업입니다"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. 완료 처리
        enrollment.status = 'completed'
        enrollment.completed_at = timezone.now()
        enrollment.save()

        logger.info(
            f"Course completed: user_id={user.id}, course_id={course.id}, "
            f"enrollment_id={enrollment.id}"
        )

        # 5. 성공 응답
        return Response(
            {
                "message": "수업이 완료되었습니다",
                "enrollment_id": enrollment.id,
                "completed_at": enrollment.completed_at.isoformat()
            },
            status=status.HTTP_200_OK
        )
