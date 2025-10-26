from rest_framework import serializers
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    결제 정보 조회용 Serializer

    응답 포함 정보:
    - 금액, 결제 방법, 결제 대상, 항목 제목, 상태
    - 응시 또는 수강 시간
    """
    target_title = serializers.SerializerMethodField(
        help_text='결제 대상 항목의 제목 (시험 또는 수업 제목)'
    )
    target_type = serializers.CharField(
        source='payment_type',
        read_only=True,
        help_text='결제 대상 유형 (test 또는 course)'
    )
    target_id = serializers.IntegerField(
        source='object_id',
        read_only=True,
        help_text='결제 대상 항목의 ID'
    )
    registration_time = serializers.SerializerMethodField(
        help_text='응시 또는 수강 신청 시간'
    )

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_type',
            'target_title',
            'target_type',
            'target_id',
            'amount',
            'payment_method',
            'status',
            'paid_at',
            'cancelled_at',
            'registration_time',  # 응시 또는 수강 시간
        ]
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': '결제 고유 ID'},
            'payment_type': {'help_text': '결제 유형 (test: 시험, course: 수업)'},
            'amount': {'help_text': '결제 금액'},
            'payment_method': {'help_text': '결제 수단 (kakaopay, card, bank_transfer)'},
            'status': {'help_text': '결제 상태 (paid: 완료, cancelled: 취소, refunded: 환불)'},
            'paid_at': {'help_text': '결제 일시'},
            'cancelled_at': {'help_text': '취소 일시'},
        }

    def get_target_title(self, obj):
        """
        GenericForeignKey로 연결된 대상(Test/Course)의 제목 반환
        대상이 삭제된 경우 None 반환
        """
        if obj.target:
            return getattr(obj.target, 'title', None)
        return None

    def get_registration_time(self, obj):
        """
        응시/수강 시간 반환
        - Test: TestRegistration.applied_at
        - Course: CourseRegistration.enrolled_at
        """
        from tests.models import TestRegistration
        from courses.models import CourseRegistration

        request = self.context.get('request')
        if not request or not request.user:
            return None

        try:
            if obj.payment_type == 'test' and obj.target:
                registration = TestRegistration.objects.filter(
                    user=request.user,
                    test=obj.target
                ).first()
                return registration.applied_at.isoformat() if registration else None
            elif obj.payment_type == 'course' and obj.target:
                registration = CourseRegistration.objects.filter(
                    user=request.user,
                    course=obj.target
                ).first()
                return registration.enrolled_at.isoformat() if registration else None
        except Exception:
            return None

        return None
