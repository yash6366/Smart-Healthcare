from django.urls import path
from .views import (
    PatientClinicalHistoryView,
    PatientDetailView,
    PatientHealthTimelineView,
    PatientListView,
    PatientMeView,
)

urlpatterns = [
    path("me/timeline/", PatientHealthTimelineView.as_view(), name="patient-health-timeline"),
    path("me/", PatientMeView.as_view(), name="patient-me"),
    path("<int:pk>/clinical-history/", PatientClinicalHistoryView.as_view(), name="patient-clinical-history"),
    path("<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("", PatientListView.as_view(), name="patient-list"),
]
