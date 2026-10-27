from django.urls import path
from .views import (
    AppointmentCancelView,
    AppointmentCompleteView,
    AppointmentConfirmView,
    AppointmentDetailView,
    AppointmentListCreateView,
    AppointmentRejectView,
    DoctorDailyScheduleView,
)

urlpatterns = [
    path("daily-schedule/", DoctorDailyScheduleView.as_view(), name="appointment-daily-schedule"),
    path("", AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("<int:pk>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path("<int:pk>/confirm/", AppointmentConfirmView.as_view(), name="appointment-confirm"),
    path("<int:pk>/reject/", AppointmentRejectView.as_view(), name="appointment-reject"),
    path("<int:pk>/cancel/", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("<int:pk>/complete/", AppointmentCompleteView.as_view(), name="appointment-complete"),
]
