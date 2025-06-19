# apps/clinical/tests/test_portal_api.py
import pytest
import jwt
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, Branch, UserProfile
from apps.clinical.models import Patient
from datetime import datetime, timedelta
from apps.clinical.models import Appointment, MedicalRecord, Prescription
 

@pytest.mark.django_db
class TestPortalAPI:
    """Groups tests for the Patient Portal API."""

    def test_patient_can_get_own_profile(self):
        """
        Tests that a logged-in user can retrieve their own linked patient profile.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        # This user represents the patient's login account from the Auth service
        patient_user = User.objects.create_user(username='patient_user', password='password123')
        
        # Create the corresponding Patient record, linking it via the user's ID
        patient_profile = Patient.objects.create(
            organization=org,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-05-20',
            external_user_id=patient_user.id # This is the crucial link
        )

        client = APIClient()
        # Authenticate by creating and sending a JWT for this user
        jwt_payload = {'user_id': patient_user.id}
        token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm='HS256')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Act
        # The endpoint implicitly knows who the user is from the token.
        response = client.get('/api/v1/portal/my-profile/')

        # 3. Assert
        assert response.status_code == 200
        # It's a list view, so we check the results
        assert len(response.data['results']) == 1
        # Check that the data returned is for the correct patient
        assert response.data['results'][0]['id'] == str(patient_profile.id)
        assert response.data['results'][0]['first_name'] == 'John'


    def test_patient_can_list_own_appointments(self):
        """
        Tests that a user can list their own appointments, but not another user's.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
        
        # Create User A and their corresponding Patient profile
        user_a = User.objects.create_user(username='user_a', password='password123')
        patient_a = Patient.objects.create(organization=org, first_name='User', last_name='A', date_of_birth='1990-01-01', external_user_id=user_a.id)

        # Create User B and their corresponding Patient profile
        user_b = User.objects.create_user(username='user_b', password='password123')
        patient_b = Patient.objects.create(organization=org, first_name='User', last_name='B', date_of_birth='1991-01-01', external_user_id=user_b.id)
        
        # Create two appointments for Patient A
        appt_a1 = Appointment.objects.create(patient=patient_a, doctor=doctor, branch=branch, start_time=datetime.now(), end_time=datetime.now())
        appt_a2 = Appointment.objects.create(patient=patient_a, doctor=doctor, branch=branch, start_time=datetime.now(), end_time=datetime.now())
        
        # Create one appointment for Patient B
        appt_b1 = Appointment.objects.create(patient=patient_b, doctor=doctor, branch=branch, start_time=datetime.now(), end_time=datetime.now())

        # Authenticate as User A
        client = APIClient()
        jwt_payload = {'user_id': user_a.id}
        token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm='HS256')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Act
        response = client.get('/api/v1/portal/my-appointments/')

        # 3. Assert
        assert response.status_code == 200
        # The user should only see their own 2 appointments
        assert response.data['count'] == 2
        
        # Check that the IDs of their appointments are present
        response_ids = {appt['id'] for appt in response.data['results']}
        assert str(appt_a1.id) in response_ids
        assert str(appt_a2.id) in response_ids
        
        # Crucially, check that Patient B's appointment is NOT present
        assert str(appt_b1.id) not in response_ids   

    def test_patient_can_retrieve_own_appointment_with_record(self):
        """
        Tests that a patient can retrieve a single appointment and see the
        nested medical record data.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor = User.objects.create_user(username='doc', password='123')
        user_a = User.objects.create_user(username='user_a', password='password123')
        patient_a = Patient.objects.create(organization=org, first_name='User', last_name='A', date_of_birth='1990-01-01', external_user_id=user_a.id)
        
        appointment = Appointment.objects.create(patient=patient_a, doctor=doctor, branch=branch, start_time=datetime.now(), end_time=datetime.now())
        medical_record = MedicalRecord.objects.create(appointment=appointment, diagnosis="Seasonal Allergies")
        Prescription.objects.create(medical_record=medical_record, medication="Loratadine", dosage="10mg", frequency="Once a day", duration_days=30)
        
        client = APIClient()
        jwt_payload = {'user_id': user_a.id}
        token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm='HS256')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Act
        # We request the detail view for this specific appointment
        response = client.get(f'/api/v1/portal/my-appointments/{appointment.id}/')

        # 3. Assert
        assert response.status_code == 200
        # Check that the nested medical record data is present and correct
        assert response.data['medical_record'] is not None
        assert response.data['medical_record']['diagnosis'] == "Seasonal Allergies"
        # Check that the nested prescription data is present
        assert len(response.data['medical_record']['prescriptions']) == 1
        assert response.data['medical_record']['prescriptions'][0]['medication'] == "Loratadine"

    def test_patient_cannot_retrieve_anothers_appointment(self):
        """
        Tests that a patient gets a 404 Not Found when trying to access an
        appointment that does not belong to them.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor = User.objects.create_user(username='doc', password='123')
        user_a = User.objects.create_user(username='user_a', password='password123')
        patient_a = Patient.objects.create(organization=org, first_name='User', last_name='A', date_of_birth='1990-01-01', external_user_id=user_a.id)

        user_b = User.objects.create_user(username='user_b', password='password123')
        patient_b = Patient.objects.create(organization=org, first_name='User', last_name='B', date_of_birth='1991-01-01', external_user_id=user_b.id)
        
        # This appointment belongs to Patient B
        appointment_b = Appointment.objects.create(patient=patient_b, doctor=doctor, branch=branch, start_time=datetime.now(), end_time=datetime.now())
        
        # We authenticate as User A
        client = APIClient()
        jwt_payload = {'user_id': user_a.id}
        token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm='HS256')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Act
        # But we try to access Patient B's appointment
        response = client.get(f'/api/v1/portal/my-appointments/{appointment_b.id}/')

        # 3. Assert
        # The get_queryset filter protects us! From User A's perspective, this
        # appointment does not exist, so we get a 404 Not Found.
        assert response.status_code == 404
