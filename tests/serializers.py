from rest_framework import serializers
from .models import Test, TestRegistration


class TestSerializer(serializers.ModelSerializer):
    """
    시험 Serializer

    추가 필드:
    - is_registered: 현재 사용자가 이미 응시 신청했는지 여부 (Boolean)
    - registration_count: 해당 시험의 총 응시자 수 (Integer)
    """
    # 추가 필드 (읽기 전용)
    is_registered = serializers.SerializerMethodField(
        help_text='현재 사용자의 응시 신청 여부'
    )
    registration_count = serializers.IntegerField(
        read_only=True,
        help_text='해당 시험의 총 응시자 수'
    )

    class Meta:
        model = Test
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
        extra_kwargs = {
            'id': {'help_text': '시험 고유 ID'},
            'title': {'help_text': '시험 제목'},
            'description': {'help_text': '시험 설명'},
            'price': {'help_text': '시험 응시 가격'},
            'start_at': {'help_text': '시험 시작 일시'},
            'end_at': {'help_text': '시험 종료 일시'},
            'created_at': {'help_text': '생성 일시'},
        }

    def get_is_registered(self, obj):
        """
        현재 사용자가 이미 응시 신청했는지 확인

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
        return TestRegistration.objects.filter(
            user=request.user,
            test=obj
        ).exists()


class TestApplySerializer(serializers.Serializer):
    """
    시험 응시 신청 Serializer

    입력 필드:
    - amount: 결제 금액
    - payment_method: 결제 수단

    출력 필드:
    - payment_id: 생성된 결제 ID
    - registration_id: 생성된 응시 등록 ID
    """
    # 입력 필드
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        help_text='결제 금액 (시험 가격과 일치해야 함)'
    )
    payment_method = serializers.ChoiceField(
        choices=['kakaopay', 'card', 'bank_transfer'],
        required=True,
        help_text='결제 수단 (kakaopay, card, bank_transfer)'
    )

    # 출력 필드 (읽기 전용)
    payment_id = serializers.IntegerField(
        read_only=True,
        help_text='생성된 결제 ID'
    )
    registration_id = serializers.IntegerField(
        read_only=True,
        help_text='생성된 응시 등록 ID'
    )

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
