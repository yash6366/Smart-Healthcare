from django.urls import path
from .views import (
    DoctorDetailView,
    DoctorListView,
    DoctorMeView,
    DoctorVerifyView,
)

urlpatterns = [
    path("me/", DoctorMeView.as_view(), name="doctor-me"),
    path("<int:pk>/verify/", DoctorVerifyView.as_view(), name="doctor-verify"),
    path("<int:pk>/", DoctorDetailView.as_view(), name="doctor-detail"),
    path("", DoctorListView.as_view(), name="doctor-list"),
]
