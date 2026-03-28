from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, MeView

urlpatterns = [
    # Register
    path("auth/register/", RegisterView.as_view(), name="auth-register"),

    # JWT login (existing + alias)
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),

    # Refresh (existing + alias)
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Me (existing + alias)
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("me/", MeView.as_view(), name="me"),
]
