from django.urls import path
from .views import AdminAnalyticsView, AuditLogDetailView, AuditLogListView

urlpatterns = [
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    path("logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("logs/<int:pk>/", AuditLogDetailView.as_view(), name="audit-log-detail"),
]
