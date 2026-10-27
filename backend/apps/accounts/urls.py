from django.urls import path
from .views import (
    ChangePasswordView,
    CookieTokenRefreshView,
    CsrfTokenView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token-refresh"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]
