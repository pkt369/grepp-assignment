from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema

from .serializers import UserSerializer, CustomTokenObtainPairSerializer


class SignupView(APIView):
    """회원가입 API"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='회원가입',
        description='새로운 사용자 계정을 생성합니다.',
        request=UserSerializer,
        responses={
            201: {'description': '회원가입 성공'},
            400: {'description': '유효성 검증 실패 (중복 이메일, 약한 비밀번호 등)'},
        },
    )
    def post(self, request):
        """
        회원가입 처리

        요청 본문:
            - email: 이메일 (필수, 고유값)
            - username: 사용자명 (필수)
            - password: 비밀번호 (필수, 최소 8자, 문자+숫자 포함)

        응답:
            - 201: 회원가입 성공
            - 400: 유효성 검증 실패
        """
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'message': '회원가입이 완료되었습니다.',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                    }
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                'message': '회원가입에 실패했습니다.',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    tags=['Auth'],
    summary='로그인',
    description='이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.',
    request=CustomTokenObtainPairSerializer,
    responses={
        200: {'description': '로그인 성공 (액세스 토큰, 리프레시 토큰 및 사용자 정보 반환)'},
        401: {'description': '인증 실패 (잘못된 이메일 또는 비밀번호)'},
    },
)
class LoginView(TokenObtainPairView):
    """
    로그인 API (JWT 토큰 발급)

    요청 본문:
        - email: 이메일
        - password: 비밀번호

    응답:
        - 200: 로그인 성공, 액세스/리프레시 토큰 발급
        - 401: 인증 실패
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

# Todo: ResetPassword