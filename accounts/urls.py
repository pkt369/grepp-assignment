from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import SignupView, LoginView

app_name = 'accounts'

urlpatterns = [
    # 회원가입
    path('signup/', SignupView.as_view(), name='signup'),

    # 로그인 (JWT 토큰 발급)
    path('login/', LoginView.as_view(), name='login'),

    # 토큰 갱신
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
