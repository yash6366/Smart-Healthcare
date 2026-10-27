import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile


@pytest.fixture
def api_client():
    return APIClient()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email
    return str(refresh.access_token), str(refresh)


@pytest.fixture
def auth_client():
    def _auth_client(user):
        client = APIClient()
        access_token, _ = get_tokens_for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return client
    return _auth_client


@pytest.fixture
def patient_user(db):
    user = User.objects.create_user(
        username="john_patient",
        email="john@example.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe",
        phone_number="+919876543210",
        role=User.Role.PATIENT,
        is_verified=True,
    )
    PatientProfile.objects.create(
        user=user,
        city="Bengaluru",
        blood_group=PatientProfile.BloodGroup.O_POS,
    )
    return user


@pytest.fixture
def second_patient_user(db):
    user = User.objects.create_user(
        username="jane_patient",
        email="jane@example.com",
        password="SecurePassword123!",
        first_name="Jane",
        last_name="Smith",
        role=User.Role.PATIENT,
        is_verified=True,
    )
    PatientProfile.objects.create(user=user)
    return user


@pytest.fixture
def doctor_user(db):
    user = User.objects.create_user(
        username="dr_sharma",
        email="sharma@vakcare.com",
        password="SecureDoctorPass123!",
        first_name="Ramesh",
        last_name="Sharma",
        role=User.Role.DOCTOR,
        is_verified=True,
    )
    DoctorProfile.objects.create(
        user=user,
        display_name="Ramesh Sharma",
        specialization=DoctorProfile.Specialization.CARDIOLOGY,
        qualifications="MBBS, MD (Cardiology)",
        years_of_experience=12,
        consultation_fee=800.00,
        biography="Senior Consultant Cardiologist",
        license_number="KMC-CAR-12345",
        is_verified=True,
        is_available=True,
        working_hours_start="09:00:00",
        working_hours_end="18:00:00",
    )
    return user


@pytest.fixture
def unverified_doctor_user(db):
    user = User.objects.create_user(
        username="dr_unverified",
        email="unverified@vakcare.com",
        password="SecureDoctorPass123!",
        first_name="Anil",
        last_name="Kumar",
        role=User.Role.DOCTOR,
        is_verified=False,
    )
    DoctorProfile.objects.create(
        user=user,
        display_name="Anil Kumar",
        specialization=DoctorProfile.Specialization.DERMATOLOGY,
        qualifications="MBBS",
        years_of_experience=2,
        consultation_fee=500.00,
        is_verified=False,
        is_available=True,
    )
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username="admin_super",
        email="admin@vakcare.com",
        password="SuperAdminPass123!",
    )
    return user
