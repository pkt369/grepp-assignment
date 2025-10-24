from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer, CustomTokenObtainPairSerializer


class SignupView(APIView):
    """회원가입 API"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        회원가입 처리

        Request Body:
            - email: 이메일 (필수, 고유값)
            - username: 사용자명 (필수)
            - password: 비밀번호 (필수, 최소 8자, 문자+숫자 포함)

        Response:
            - 201 Created: 회원가입 성공
            - 400 Bad Request: 유효성 검증 실패
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


class LoginView(TokenObtainPairView):
    """
    로그인 API (JWT 토큰 발급)

    Request Body:
        - email: 이메일
        - password: 비밀번호

    Response:
        - 200 OK: 로그인 성공, access/refresh 토큰 발급
        - 401 Unauthorized: 인증 실패
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

# Todo: ResetPassword