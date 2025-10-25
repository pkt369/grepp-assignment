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
    is_registered = serializers.SerializerMethodField()
    registration_count = serializers.IntegerField(read_only=True)

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
