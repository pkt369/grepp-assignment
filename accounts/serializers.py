import re
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """회원가입용 Serializer"""
    email = serializers.EmailField(
        required=True,
        help_text='이메일 주소 (로그인 ID로 사용, 고유값)',
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='이미 사용 중인 이메일입니다.'
            )
        ]
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='비밀번호 (최소 8자, 문자와 숫자 포함)'
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password']
        extra_kwargs = {
            'id': {'help_text': '사용자 고유 ID'},
            'username': {
                'required': True,
                'help_text': '사용자 이름'
            },
        }

    def validate_password(self, value):
        """비밀번호 강도 검증"""
        if len(value) < 8:
            raise serializers.ValidationError("비밀번호는 최소 8자 이상이어야 합니다.")

        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("비밀번호는 최소 하나의 문자를 포함해야 합니다.")

        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("비밀번호는 최소 하나의 숫자를 포함해야 합니다.")

        return value

    def create(self, validated_data):
        """비밀번호 해싱하여 사용자 생성"""
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']  # create_user가 자동으로 해싱
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """커스텀 로그인 Serializer"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # 토큰에 추가 정보 포함
        token['email'] = user.email
        token['username'] = user.username

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # 응답에 사용자 정보 추가
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
        }

        return data
