from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """COMMUNICATION Domain: In-app notifications (table: notifications_notification)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
