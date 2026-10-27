from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    List notifications for the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        unread_only = self.request.query_params.get("unread")
        if unread_only and unread_only.lower() in ("true", "1"):
            qs = qs.filter(is_read=False)
        return qs

    @extend_schema(
        tags=["Notifications"],
        summary="List User Notifications",
        parameters=[
            OpenApiParameter(name="unread", description="Filter by unread notifications only", required=False, type=bool),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NotificationMarkReadView(APIView):
    """
    Mark a specific notification as read.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark Notification as Read",
        request=None,
        responses={200: NotificationSerializer},
    )
    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": "RESOURCE_NOT_FOUND", "message": "Notification not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()

        return Response(
            {"status": "success", "notification": NotificationSerializer(notification).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        """Allow POST in addition to PATCH for broader client compatibility."""
        return self.patch(request, pk)


class NotificationMarkAllReadView(APIView):
    """
    Mark all unread notifications for the authenticated user as read.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark All Notifications as Read",
        request=None,
        responses={
            200: inline_serializer(
                name="MarkAllReadResponse",
                fields={
                    "status": serializers.CharField(default="success"),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        now = timezone.now()
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True,
            read_at=now,
        )
        return Response(
            {"status": "success", "message": f"{updated_count} notifications marked as read."},
            status=status.HTTP_200_OK,
        )


class NotificationTriggerRemindersView(APIView):
    """
    Trigger automated scanning and delivery of upcoming appointment reminders.
    Restricted to Platform Administrators or automated system workers.
    """
    from apps.accounts.permissions import IsAdministrator
    permission_classes = [IsAdministrator]

    @extend_schema(
        tags=["Notifications"],
        summary="Trigger Appointment Reminders (Admin Only)",
        responses={
            200: inline_serializer(
                name="TriggerRemindersResponse",
                fields={
                    "status": serializers.CharField(default="success"),
                    "reminders_generated": serializers.IntegerField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        from .services import generate_appointment_reminders
        lead_hours = int(request.data.get("lead_hours", 48))
        count = generate_appointment_reminders(lead_hours=lead_hours)
        return Response(
            {
                "status": "success",
                "reminders_generated": count,
                "message": f"Successfully generated {count} appointment reminders.",
            },
            status=status.HTTP_200_OK,
        )
