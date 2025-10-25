from rest_framework import serializers
from .models import Course, CourseRegistration


class CourseSerializer(serializers.ModelSerializer):
    """
    수업 Serializer

    추가 필드:
    - is_registered: 현재 사용자가 이미 수강 신청했는지 여부 (Boolean)
    - registration_count: 해당 수업의 총 수강자 수 (Integer)
    """
    # 추가 필드 (읽기 전용)
    is_registered = serializers.SerializerMethodField()
    registration_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'price',
            'start_at',
            'end_at',
            'created_at',
            'is_registered',
            'registration_count',
        ]
        read_only_fields = ['id', 'created_at']

    def get_is_registered(self, obj):
        """
        현재 사용자가 이미 수강 신청했는지 확인

        ViewSet에서 annotate로 is_registered_flag를 추가 => N+1 문제 방지 ( 어플리케이션 레벨에서 방지: 중복된 디비 네트워크 연결 최소화 )
        """
        request = self.context.get('request')

        # 비인증 사용자
        if not request or not hasattr(request, 'user') or request.user is None or not request.user.is_authenticated:
            return False

        # ViewSet에서 annotate로 추가한 필드 사용 (성능 최적화)
        if hasattr(obj, 'is_registered_flag'):
            return obj.is_registered_flag

        # Fallback: 직접 조회 ( 비효율적: N + 1 문제 발생 가능 )
        return CourseRegistration.objects.filter(
            user=request.user,
            course=obj
        ).exists()


class CourseEnrollSerializer(serializers.Serializer):
    """
    수업 수강 신청 Serializer

    입력 필드:
    - amount: 결제 금액
    - payment_method: 결제 수단

    출력 필드:
    - payment_id: 생성된 결제 ID
    - enrollment_id: 생성된 수강 등록 ID
    """
    # 입력 필드
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True
    )
    payment_method = serializers.ChoiceField(
        choices=['kakaopay', 'card', 'bank_transfer'],
        required=True
    )

    # 출력 필드 (읽기 전용)
    payment_id = serializers.IntegerField(read_only=True)
    enrollment_id = serializers.IntegerField(read_only=True)

    def validate_amount(self, value):
        """금액 검증"""
        if value <= 0:
            raise serializers.ValidationError("금액은 0보다 커야 합니다")
        # if value > 100000000:  # 1억
        #     raise serializers.ValidationError("금액은 1억을 초과할 수 없습니다")
        return value

    def validate_payment_method(self, value):
        """결제 수단 검증"""
        valid_methods = ['kakaopay', 'card', 'bank_transfer']
        if value not in valid_methods:
            raise serializers.ValidationError(
                f"유효하지 않은 결제 수단입니다. 선택 가능: {', '.join(valid_methods)}"
            )
        return value
