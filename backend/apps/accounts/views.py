from datetime import timedelta
from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.audit.services import log_audit_event

REFRESH_COOKIE_NAME = "vakcare_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Sets an HttpOnly, secure, SameSite=Lax cookie for the refresh token."""
    max_age = int(timedelta(days=getattr(settings, "REFRESH_DAYS", 7)).total_seconds())
    secure_cookie = not settings.DEBUG and getattr(settings, "SESSION_COOKIE_SECURE", True)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookie,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def delete_refresh_cookie(response: Response) -> None:
    """Deletes the HttpOnly refresh token cookie upon logout."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


class RegisterView(APIView):
    """
    Public registration endpoint for patients.
    Creates a new user with the PATIENT role and provisions their initial patient profile.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Register New Patient Account",
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Audit log registration event
        log_audit_event(
            event_type="AUTH_REGISTER",
            actor=user,
            resource_type="User",
            resource_id=str(user.id),
            action="PATIENT_REGISTER",
            details={"email": user.email, "role": user.role},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": "Account registered successfully. You can now log in.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    User authentication endpoint returning JWT tokens and user profile information.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        summary="Authenticate User and Obtain JWT Tokens",
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name="LoginSuccessResponse",
                fields={
                    "status": serializers.CharField(default="success"),
                    "user": UserSerializer(),
                    "tokens": inline_serializer(
                        name="TokenPair",
                        fields={
                            "access": serializers.CharField(),
                            "refresh": serializers.CharField(),
                        },
                    ),
                },
            )
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            log_audit_event(
                event_type="AUTH_LOGIN",
                resource_type="User",
                action="USER_LOGIN_FAILED",
                details={"identifier": request.data.get("email_or_username")},
                is_success=False,
                request=request,
            )
            return Response(
                {
                    "status": "error",
                    "error": {
                        "code": "AUTHENTICATION_FAILED",
                        "message": "Invalid credentials. Please verify your username/email and password.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = serializer.validated_data
        user = data["user"]

        log_audit_event(
            event_type="AUTH_LOGIN",
            actor=user,
            resource_type="User",
            resource_id=str(user.id),
            action="USER_LOGIN_SUCCESS",
            is_success=True,
            request=request,
        )

        response = Response(
            {
                "status": "success",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": data["access"],
                    "refresh": data["refresh"],
                },
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, data["refresh"])
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """
    Enhanced TokenRefreshView supporting refresh token delivery via either JSON body
    or an HttpOnly cookie ('vakcare_refresh_token').
    Rotated refresh tokens are automatically updated in the HttpOnly cookie.
    """

    def post(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if "refresh" not in data or not data["refresh"]:
            cookie_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
            if cookie_token:
                data["refresh"] = cookie_token

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        response_data = serializer.validated_data
        response = Response(response_data, status=status.HTTP_200_OK)

        new_refresh = response_data.get("refresh")
        if new_refresh:
            set_refresh_cookie(response, new_refresh)

        return response


class LogoutView(APIView):
    """
    Logout endpoint that invalidates the given refresh token using SimpleJWT blacklist.
    Extracts refresh token from JSON payload or the HttpOnly cookie and clears the cookie.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Logout and Blacklist Refresh Token",
        request=LogoutSerializer,
        responses={200: inline_serializer(name="LogoutResponse", fields={"status": serializers.CharField()})},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_token:
            return Response(
                {
                    "status": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Refresh token is required to invalidate session.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LogoutSerializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        log_audit_event(
            event_type="AUTH_LOGOUT",
            actor=request.user,
            resource_type="User",
            resource_id=str(request.user.id),
            action="USER_LOGOUT",
            is_success=True,
            request=request,
        )

        response = Response(
            {"status": "success", "message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )
        delete_refresh_cookie(response)
        return response


class CsrfTokenView(APIView):
    """
    Returns a fresh CSRF token for cookie-authenticated clients.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Retrieve CSRF Token",
        responses={200: inline_serializer(name="CsrfResponse", fields={"status": serializers.CharField(), "csrfToken": serializers.CharField()})},
    )
    def get(self, request):
        token = get_token(request)
        return Response({"status": "success", "csrfToken": token}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the currently authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    @extend_schema(tags=["Auth"], summary="Get Current Authenticated User")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Auth"], summary="Update Current Authenticated User")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    Endpoint for authenticated users to change their password securely.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Change Password",
        request=ChangePasswordSerializer,
        responses={200: inline_serializer(name="PasswordChangeResponse", fields={"status": serializers.CharField()})},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        log_audit_event(
            event_type="AUTH_PASSWORD_CHANGE",
            actor=request.user,
            resource_type="User",
            resource_id=str(request.user.id),
            action="PASSWORD_CHANGED",
            is_success=True,
            request=request,
        )

        return Response(
            {"status": "success", "message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )
