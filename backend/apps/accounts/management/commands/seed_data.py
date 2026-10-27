import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile
from apps.appointments.models import Appointment
from apps.medical_records.models import MedicalRecord
from apps.prescriptions.models import Prescription, PrescriptionItem
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Seeds database with administrative superuser, diverse verified/unverified doctors, and patient profiles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Beginning database seeding process..."))

        with transaction.atomic():
            # 1. Administrator User
            admin_user, created = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@vakcare.com",
                    "first_name": "System",
                    "last_name": "Administrator",
                    "phone_number": "+919800000001",
                    "role": User.Role.ADMIN,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_verified": True,
                    "is_active": True,
                },
            )
            admin_user.set_password("SuperAdminPass123!")
            admin_user.role = User.Role.ADMIN
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_verified = True
            admin_user.save()
            status_text = "Created" if created else "Updated password for"
            self.stdout.write(self.style.SUCCESS(f"[ADMIN] {status_text} admin (admin@vakcare.com)"))

            # 2. Doctors
            doctors_data = [
                {
                    "username": "dr_sharma",
                    "email": "sharma@vakcare.com",
                    "first_name": "Ramesh",
                    "last_name": "Sharma",
                    "phone_number": "+919811111101",
                    "password": "Doctor123!",
                    "display_name": "Ramesh Sharma",
                    "specialization": DoctorProfile.Specialization.CARDIOLOGY,
                    "qualifications": "MBBS, MD (Cardiology), DM",
                    "years_of_experience": 15,
                    "consultation_fee": Decimal("800.00"),
                    "license_number": "KMC-CAR-10824",
                    "biography": "Senior Interventional Cardiologist specializing in cardiovascular diagnostics, preventative cardiology, and echocardiography.",
                    "is_verified": True,
                    "is_available": True,
                    "working_hours_start": datetime.time(9, 0),
                    "working_hours_end": datetime.time(17, 0),
                },
                {
                    "username": "dr_priya",
                    "email": "priya.patel@vakcare.com",
                    "first_name": "Priya",
                    "last_name": "Patel",
                    "phone_number": "+919811111102",
                    "password": "Doctor123!",
                    "display_name": "Priya Patel",
                    "specialization": DoctorProfile.Specialization.DERMATOLOGY,
                    "qualifications": "MBBS, MD (Dermatology & Venereology)",
                    "years_of_experience": 11,
                    "consultation_fee": Decimal("600.00"),
                    "license_number": "MMC-DERM-45129",
                    "biography": "Consultant Dermatologist with clinical focus on medical dermatology, allergic dermatitis, and modern skin wellness therapies.",
                    "is_verified": True,
                    "is_available": True,
                    "working_hours_start": datetime.time(10, 0),
                    "working_hours_end": datetime.time(18, 0),
                },
                {
                    "username": "dr_rajesh",
                    "email": "rajesh.verma@vakcare.com",
                    "first_name": "Rajesh",
                    "last_name": "Verma",
                    "phone_number": "+919811111103",
                    "password": "Doctor123!",
                    "display_name": "Rajesh Verma",
                    "specialization": DoctorProfile.Specialization.GENERAL_MEDICINE,
                    "qualifications": "MBBS, MD (General Medicine)",
                    "years_of_experience": 18,
                    "consultation_fee": Decimal("500.00"),
                    "license_number": "DMC-MED-22901",
                    "biography": "Internal Medicine Specialist focused on chronic disease management, diabetes, hypertensive care, and geriatric health.",
                    "is_verified": True,
                    "is_available": True,
                    "working_hours_start": datetime.time(8, 30),
                    "working_hours_end": datetime.time(16, 30),
                },
                {
                    "username": "dr_ananya",
                    "email": "ananya.iyer@vakcare.com",
                    "first_name": "Ananya",
                    "last_name": "Iyer",
                    "phone_number": "+919811111104",
                    "password": "Doctor123!",
                    "display_name": "Ananya Iyer",
                    "specialization": DoctorProfile.Specialization.PEDIATRICS,
                    "qualifications": "MBBS, DCH, DNB (Pediatrics)",
                    "years_of_experience": 8,
                    "consultation_fee": Decimal("550.00"),
                    "license_number": "TMC-PED-67341",
                    "biography": "Pediatrician and Child Care Specialist dedicated to neonatal wellness, developmental tracking, and adolescent medicine.",
                    "is_verified": True,
                    "is_available": True,
                    "working_hours_start": datetime.time(9, 30),
                    "working_hours_end": datetime.time(17, 30),
                },
                {
                    "username": "dr_vikram",
                    "email": "vikram.malhotra@vakcare.com",
                    "first_name": "Vikram",
                    "last_name": "Malhotra",
                    "phone_number": "+919811111105",
                    "password": "Doctor123!",
                    "display_name": "Vikram Malhotra",
                    "specialization": DoctorProfile.Specialization.ORTHOPEDICS,
                    "qualifications": "MBBS, MS (Orthopedics)",
                    "years_of_experience": 14,
                    "consultation_fee": Decimal("750.00"),
                    "license_number": "KMC-ORTH-55219",
                    "biography": "Orthopedic Surgeon with extensive expertise in joint health, sports injury rehabilitation, and arthroscopic intervention.",
                    "is_verified": True,
                    "is_available": True,
                    "working_hours_start": datetime.time(10, 0),
                    "working_hours_end": datetime.time(17, 0),
                },
                {
                    "username": "dr_sneha",
                    "email": "sneha.reddy@vakcare.com",
                    "first_name": "Sneha",
                    "last_name": "Reddy",
                    "phone_number": "+919811111106",
                    "password": "Doctor123!",
                    "display_name": "Sneha Reddy",
                    "specialization": DoctorProfile.Specialization.NEUROLOGY,
                    "qualifications": "MBBS, MD, DM (Neurology)",
                    "years_of_experience": 7,
                    "consultation_fee": Decimal("900.00"),
                    "license_number": "APMC-NEUR-88123",
                    "biography": "Neurologist specializing in migraine treatment, neuro-rehabilitation, and neuromuscular diagnostic evaluations.",
                    "is_verified": False,  # Pending verification for testing admin verification portal!
                    "is_available": True,
                    "working_hours_start": datetime.time(11, 0),
                    "working_hours_end": datetime.time(19, 0),
                },
            ]

            doctor_instances = {}
            for d in doctors_data:
                user, _ = User.objects.get_or_create(
                    username=d["username"],
                    defaults={
                        "email": d["email"],
                        "first_name": d["first_name"],
                        "last_name": d["last_name"],
                        "phone_number": d["phone_number"],
                        "role": User.Role.DOCTOR,
                        "is_verified": d["is_verified"],
                        "is_active": True,
                    },
                )
                user.set_password(d["password"])
                user.role = User.Role.DOCTOR
                user.is_verified = d["is_verified"]
                user.save()

                doc_prof, _ = DoctorProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "display_name": d["display_name"],
                        "specialization": d["specialization"],
                        "qualifications": d["qualifications"],
                        "years_of_experience": d["years_of_experience"],
                        "consultation_fee": d["consultation_fee"],
                        "license_number": d["license_number"],
                        "biography": d["biography"],
                        "is_verified": d["is_verified"],
                        "is_available": d["is_available"],
                        "working_hours_start": d["working_hours_start"],
                        "working_hours_end": d["working_hours_end"],
                    },
                )
                doctor_instances[d["username"]] = doc_prof
                verified_str = "Verified" if d["is_verified"] else "Pending Verification"
                self.stdout.write(self.style.SUCCESS(f"[DOCTOR] Dr. {doc_prof.display_name} ({d['specialization']}) - {verified_str}"))

            # 3. Patients
            patients_data = [
                {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone_number": "+919822222201",
                    "password": "Patient123!",
                    "date_of_birth": datetime.date(1988, 6, 15),
                    "gender": PatientProfile.Gender.MALE,
                    "blood_group": PatientProfile.BloodGroup.O_POS,
                    "emergency_contact_name": "Jane Doe",
                    "emergency_contact_phone": "+919822222291",
                    "emergency_contact_relation": "Spouse",
                    "address": "#42, Palm Meadows, Indiranagar",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "postal_code": "560038",
                },
                {
                    "username": "jane_smith",
                    "email": "jane.smith@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "phone_number": "+919822222202",
                    "password": "Patient123!",
                    "date_of_birth": datetime.date(1994, 11, 20),
                    "gender": PatientProfile.Gender.FEMALE,
                    "blood_group": PatientProfile.BloodGroup.A_POS,
                    "emergency_contact_name": "Robert Smith",
                    "emergency_contact_phone": "+919822222292",
                    "emergency_contact_relation": "Father",
                    "address": "Flat 802, Marina Bay Towers, Bandra West",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "postal_code": "400050",
                },
                {
                    "username": "aarav_sharma",
                    "email": "aarav@example.com",
                    "first_name": "Aarav",
                    "last_name": "Sharma",
                    "phone_number": "+919822222203",
                    "password": "Patient123!",
                    "date_of_birth": datetime.date(2001, 3, 10),
                    "gender": PatientProfile.Gender.MALE,
                    "blood_group": PatientProfile.BloodGroup.B_POS,
                    "emergency_contact_name": "Sunita Sharma",
                    "emergency_contact_phone": "+919822222293",
                    "emergency_contact_relation": "Mother",
                    "address": "B-12, Green Park Extension",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "postal_code": "110016",
                },
                {
                    "username": "fatima_khan",
                    "email": "fatima@example.com",
                    "first_name": "Fatima",
                    "last_name": "Khan",
                    "phone_number": "+919822222204",
                    "password": "Patient123!",
                    "date_of_birth": datetime.date(1996, 8, 25),
                    "gender": PatientProfile.Gender.FEMALE,
                    "blood_group": PatientProfile.BloodGroup.AB_POS,
                    "emergency_contact_name": "Tariq Khan",
                    "emergency_contact_phone": "+919822222294",
                    "emergency_contact_relation": "Brother",
                    "address": "Plot 105, Banjara Hills Road No. 12",
                    "city": "Hyderabad",
                    "state": "Telangana",
                    "postal_code": "500034",
                },
            ]

            patient_instances = {}
            for p in patients_data:
                user, _ = User.objects.get_or_create(
                    username=p["username"],
                    defaults={
                        "email": p["email"],
                        "first_name": p["first_name"],
                        "last_name": p["last_name"],
                        "phone_number": p["phone_number"],
                        "role": User.Role.PATIENT,
                        "is_verified": True,
                        "is_active": True,
                    },
                )
                user.set_password(p["password"])
                user.role = User.Role.PATIENT
                user.is_verified = True
                user.save()

                pat_prof, _ = PatientProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "date_of_birth": p["date_of_birth"],
                        "gender": p["gender"],
                        "blood_group": p["blood_group"],
                        "emergency_contact_name": p["emergency_contact_name"],
                        "emergency_contact_phone": p["emergency_contact_phone"],
                        "emergency_contact_relation": p["emergency_contact_relation"],
                        "address": p["address"],
                        "city": p["city"],
                        "state": p["state"],
                        "postal_code": p["postal_code"],
                    },
                )
                patient_instances[p["username"]] = pat_prof
                self.stdout.write(self.style.SUCCESS(f"[PATIENT] {pat_prof.user.get_full_name()} ({p['blood_group']}, {p['city']})"))

            # 4. Realistic Appointments
            today = timezone.localdate()
            tomorrow = today + datetime.timedelta(days=1)
            yesterday = today - datetime.timedelta(days=1)

            # Appointment 1: Confirmed upcoming appointment
            appt1, _ = Appointment.objects.update_or_create(
                patient=patient_instances["john_doe"],
                doctor=doctor_instances["dr_sharma"],
                appointment_date=tomorrow,
                start_time=datetime.time(10, 0),
                defaults={
                    "end_time": datetime.time(10, 30),
                    "duration_minutes": 30,
                    "reason": "Routine quarterly cardiovascular health checkup and BP review.",
                    "status": Appointment.Status.CONFIRMED,
                },
            )

            # Appointment 2: Pending appointment for Dr. Priya Patel
            appt2, _ = Appointment.objects.update_or_create(
                patient=patient_instances["jane_smith"],
                doctor=doctor_instances["dr_priya"],
                appointment_date=tomorrow,
                start_time=datetime.time(14, 0),
                defaults={
                    "end_time": datetime.time(14, 30),
                    "duration_minutes": 30,
                    "reason": "Persistent dry skin patches and seasonal contact dermatitis consultation.",
                    "status": Appointment.Status.PENDING,
                },
            )

            # Appointment 3: Completed consultation yesterday
            appt3, _ = Appointment.objects.update_or_create(
                patient=patient_instances["aarav_sharma"],
                doctor=doctor_instances["dr_rajesh"],
                appointment_date=yesterday,
                start_time=datetime.time(11, 0),
                defaults={
                    "end_time": datetime.time(11, 30),
                    "duration_minutes": 30,
                    "reason": "Annual comprehensive executive health wellness screening.",
                    "status": Appointment.Status.COMPLETED,
                },
            )
            self.stdout.write(self.style.SUCCESS("[APPOINTMENTS] Created Confirmed, Pending, and Completed appointments."))

            # 5. Medical Records (EHR) for Completed Consultation
            med_rec, _ = MedicalRecord.objects.update_or_create(
                patient=patient_instances["aarav_sharma"],
                title="Annual Comprehensive Wellness Evaluation",
                defaults={
                    "doctor": doctor_instances["dr_rajesh"],
                    "record_type": MedicalRecord.RecordType.CONSULTATION_NOTE,
                    "description": "Patient presented for annual physical evaluation. Normal S1/S2 heart sounds, bilateral clear lungs. Mild seasonal allergic rhinitis observed. Advised oral antihistamine course and hydration.",
                    "clinical_data": {
                        "blood_pressure": "118/76 mmHg",
                        "heart_rate": 72,
                        "temperature": "98.4 F",
                        "respiratory_rate": 16,
                        "bmi": 22.4,
                        "oxygen_saturation": "99%",
                    },
                },
            )
            self.stdout.write(self.style.SUCCESS(f"[EHR] Created Medical Record: {med_rec.title}"))

            # 6. Prescriptions for Completed Consultation
            rx, rx_created = Prescription.objects.update_or_create(
                patient=patient_instances["aarav_sharma"],
                doctor=doctor_instances["dr_rajesh"],
                appointment=appt3,
                defaults={
                    "diagnosis": "Mild Seasonal Allergic Rhinitis & General Health Maintenance",
                    "notes": "Take medication with water after food. Maintain 3 liters of water intake daily.",
                    "status": Prescription.Status.ACTIVE,
                },
            )
            if rx_created or not rx.items.exists():
                rx.items.all().delete()
                PrescriptionItem.objects.create(
                    prescription=rx,
                    medication_name="Levocetirizine 5mg",
                    dosage="1 Tablet",
                    frequency="Once daily at bedtime",
                    duration="5 days",
                    instructions="Take after dinner with a full glass of water.",
                )
                PrescriptionItem.objects.create(
                    prescription=rx,
                    medication_name="Vitamin C + Zinc 500mg",
                    dosage="1 Chewable Tablet",
                    frequency="Once daily in morning",
                    duration="15 days",
                    instructions="Chew thoroughly after morning breakfast.",
                )
            self.stdout.write(self.style.SUCCESS(f"[PRESCRIPTION] Issued Prescription #{rx.id} with 2 medication items."))

            # 7. Notifications
            Notification.objects.get_or_create(
                recipient=patient_instances["john_doe"].user,
                title="Appointment Confirmed with Dr. Ramesh Sharma",
                defaults={
                    "notification_type": Notification.NotificationType.APPOINTMENT_CONFIRMED,
                    "message": f"Your consultation appointment with Dr. Ramesh Sharma is confirmed for tomorrow at 10:00 AM.",
                    "is_read": False,
                    "data": {"appointment_id": appt1.id},
                },
            )
            Notification.objects.get_or_create(
                recipient=doctor_instances["dr_priya"].user,
                title="New Appointment Request from Jane Smith",
                defaults={
                    "notification_type": Notification.NotificationType.APPOINTMENT_REQUESTED,
                    "message": f"Patient Jane Smith has requested an appointment for tomorrow at 02:00 PM.",
                    "is_read": False,
                    "data": {"appointment_id": appt2.id},
                },
            )
            self.stdout.write(self.style.SUCCESS("[NOTIFICATIONS] Seeded real-time notifications."))

        self.stdout.write(self.style.SUCCESS("\nDatabase seeding completed successfully!"))
