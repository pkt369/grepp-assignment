from rest_framework import serializers
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    결제 정보 조회용 Serializer

    응답 포함 정보:
    - 금액, 결제 방법, 결제 대상, 항목 제목, 상태
    - 응시 또는 수강 시간
    """
    target_title = serializers.SerializerMethodField()
    target_type = serializers.CharField(source='payment_type', read_only=True)
    target_id = serializers.IntegerField(source='object_id', read_only=True)
    registration_time = serializers.SerializerMethodField()

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
