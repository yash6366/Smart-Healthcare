from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


class HealthCheckView(APIView):
    """
    Liveness probe endpoint.
    Returns basic application health status without exposing sensitive environment or infrastructure details.
    """
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        tags=["Health"],
        summary="Service Liveness Check",
        description="Returns basic application health status.",
        responses={
            200: inline_serializer(
                name="HealthResponse",
                fields={
                    "status": serializers.CharField(default="healthy"),
                    "service": serializers.CharField(default="vakcare-backend"),
                },
            )
        },
    )
    def get(self, request):
        return Response(
            {
                "status": "healthy",
                "service": "vakcare-backend",
            },
            status=status.HTTP_200_OK,
        )


class ReadinessCheckView(APIView):
    """
    Readiness probe endpoint.
    Verifies that the database backend is responsive and ready to accept incoming traffic.
    """
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        tags=["Health"],
        summary="Service Readiness Check",
        description="Verifies essential dependencies (database connectivity) without leaking internal topology.",
        responses={
            200: inline_serializer(
                name="ReadinessSuccessResponse",
                fields={
                    "status": serializers.CharField(default="ready"),
                    "database": serializers.CharField(default="connected"),
                },
            ),
            503: inline_serializer(
                name="ReadinessErrorResponse",
                fields={
                    "status": serializers.CharField(default="unready"),
                    "database": serializers.CharField(default="unavailable"),
                },
            ),
        },
    )
    def get(self, request):
        db_ready = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    db_ready = True
        except Exception:
            db_ready = False

        if db_ready:
            from django.conf import settings
            return Response(
                {
                    "status": "ready",
                    "database": "connected",
                    "ai_provider": getattr(settings, "AI_PROVIDER", "mock"),
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "unready",
                "database": "unavailable",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
