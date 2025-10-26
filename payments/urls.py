from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import PaymentViewSet, PaymentCancelViewSet

# /api/me/payments/ - 본인 결제 내역 조회용
me_router = DefaultRouter()
me_router.register(r'', PaymentViewSet, basename='my-payment')

# /api/payments/ - 결제 취소용
payment_router = DefaultRouter()
payment_router.register(r'', PaymentCancelViewSet, basename='payment')

# 두 개의 URL 패턴을 각각 export
me_urlpatterns = me_router.urls
payment_urlpatterns = payment_router.urls
