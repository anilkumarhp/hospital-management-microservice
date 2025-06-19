# apps/clinical/tests/test_appointments_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch
from apps.clinical.models import Patient, Appointment, MedicalRecord, Prescription
from datetime import datetime, timedelta
from apps.billing.models import Charge, Service

@pytest.mark.django_db
class TestAppointmentAPI:
    """Groups all tests for the Appointment API endpoint."""

    def test_create_appointment_succeeds(self):
        """
        Tests that an authorized user (Doctor/Admin) can create an appointment.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        
        doctor_user = User.objects.create_user(username='testdoctor', password='password123', first_name='Test', last_name='Doctor')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)
        
        patient = Patient.objects.create(first_name='John', last_name='Doe', organization=org, date_of_birth='1990-05-20')

        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=30)

        appointment_payload = {
            'patient_id': patient.id,
            'doctor_id': doctor_user.id,
            'branch_id': branch.id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'notes': 'Patient reports a slight cough.'
        }

        # 2. Act
        response = client.post('/api/v1/clinical/appointments/', appointment_payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert Appointment.objects.count() == 1
        new_appointment = Appointment.objects.get()
        assert new_appointment.patient == patient
        assert new_appointment.doctor == doctor_user
        assert new_appointment.branch == branch

    def test_create_appointment_for_patient_in_another_org_fails(self):
        """
        Tests that a doctor from Org A CANNOT create an appointment for a patient from Org B.
        This proves our custom serializer validation is working.
        """
        # 1. Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')
        branch_a = Branch.objects.create(name='Main Branch', organization=org_a, city='Testville')
        
        doctor_a = User.objects.create_user(username='doctor_a', password='password123')
        UserProfile.objects.create(user=doctor_a, organization=org_a, role=UserProfile.Roles.DOCTOR)
        
        # This patient belongs to the WRONG organization
        patient_b = Patient.objects.create(first_name='Intruder', last_name='Sam', organization=org_b, date_of_birth='1995-01-01')

        client = APIClient()
        client.force_authenticate(user=doctor_a)

        payload = {
            'patient_id': patient_b.id,
            'doctor_id': doctor_a.id,
            'branch_id': branch_a.id,
            'start_time': (datetime.now() + timedelta(days=2)).isoformat(),
            'end_time': (datetime.now() + timedelta(days=2, minutes=30)).isoformat(),
        }

        # 2. Act
        response = client.post('/api/v1/clinical/appointments/', payload, format='json')

        # 3. Assert
        assert response.status_code == 400
        assert "This patient does not belong to your organization" in str(response.data)

    def test_create_appointment_with_receptionist_role_fails(self):
        """
        Tests that a user with a RECEPTIONIST role cannot create an appointment,
        as per our CanManagePatients permission class.
        """
        # 1. Arrange
        org_a = Organization.objects.create(name='Clinic A')
        branch_a = Branch.objects.create(name='Main Branch', organization=org_a, city='Testville')
        patient_a = Patient.objects.create(first_name='John', last_name='Doe', organization=org_a, date_of_birth='1990-05-20')
        doctor_user = User.objects.create_user(username='doc', password='password123')
        UserProfile.objects.create(user=doctor_user, organization=org_a, role=UserProfile.Roles.DOCTOR)

        # Create a user with the RECEPTIONIST role
        receptionist_user = User.objects.create_user(username='reception', password='password123')
        UserProfile.objects.create(user=receptionist_user, organization=org_a, role=UserProfile.Roles.RECEPTIONIST)

        client = APIClient()
        client.force_authenticate(user=receptionist_user)

        payload = {
            'patient_id': patient_a.id,
            'doctor_id': doctor_user.id,
            'branch_id': branch_a.id,
            'start_time': (datetime.now() + timedelta(days=3)).isoformat(),
            'end_time': (datetime.now() + timedelta(days=3, minutes=30)).isoformat(),
        }

        # 2. Act
        response = client.post('/api/v1/clinical/appointments/', payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden!

    def test_create_medical_record_for_appointment(self):
        """
        Tests that a doctor can create a medical record for an appointment in their org.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='2000-01-01')
        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, branch=branch,
            start_time=datetime.now(), end_time=datetime.now() + timedelta(minutes=30)
        )

        client = APIClient()
        client.force_authenticate(user=doctor)

        record_payload = {
            "diagnosis": "Common cold",
            "notes": "Advised rest and fluids."
        }

        # Construct the nested URL
        url = f'/api/v1/clinical/appointments/{appointment.id}/medical-record/'

        # 2. Act
        response = client.post(url, record_payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert MedicalRecord.objects.count() == 1
        new_record = MedicalRecord.objects.get()
        assert new_record.appointment == appointment
        assert new_record.diagnosis == "Common cold"

    # ★-- ADD THIS SECOND NEW TEST METHOD --★
    def test_create_prescription_for_medical_record(self):
        """
        Tests that a doctor can add a prescription to a medical record.
        """
        # 1. Arrange (similar setup)
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='2000-01-01')
        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, branch=branch,
            start_time=datetime.now(), end_time=datetime.now() + timedelta(minutes=30)
        )
        medical_record = MedicalRecord.objects.create(appointment=appointment, diagnosis="Flu")

        client = APIClient()
        client.force_authenticate(user=doctor)
        
        prescription_payload = {
            "medication": "Tamiflu",
            "dosage": "75mg",
            "frequency": "Twice a day",
            "duration_days": 5
        }

        # Construct the deeply nested URL
        url = f'/api/v1/clinical/medical-records/{medical_record.id}/prescriptions/'

        # 2. Act
        response = client.post(url, prescription_payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert Prescription.objects.count() == 1
        new_prescription = Prescription.objects.get()
        assert new_prescription.medical_record == medical_record
        assert new_prescription.medication == "Tamiflu"

    def test_complete_appointment_creates_charge(self):
        """
        Tests that calling the /complete/ action changes the appointment status
        and creates a corresponding charge for the patient.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        
        # Create the service that will be billed
        consultation_service = Service.objects.create(
            name='Standard Consultation',
            organization=org,
            category=Service.ServiceCategory.CONSULTATION,
            price=200.00
        )

        doctor = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
        
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='1990-01-01')
        
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            branch=branch,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            status=Appointment.AppointmentStatus.SCHEDULED # Starts as scheduled
        )

        client = APIClient()
        client.force_authenticate(user=doctor)

        # Construct the custom action URL
        url = f'/api/v1/clinical/appointments/{appointment.id}/complete/'

        # 2. Act
        response = client.post(url)

        # 3. Assert
        assert response.status_code == 200
        
        # Check that the appointment status was updated in the database
        appointment.refresh_from_db()
        assert appointment.status == Appointment.AppointmentStatus.COMPLETED
        
        # Check that a charge was created
        assert Charge.objects.count() == 1
        new_charge = Charge.objects.get()
        assert new_charge.patient == patient
        assert new_charge.service == consultation_service
        assert new_charge.total_price == 200.00
