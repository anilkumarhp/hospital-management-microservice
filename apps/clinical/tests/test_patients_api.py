# apps/clinical/tests/test_patients_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
from apps.clinical.models import Patient

@pytest.mark.django_db
class TestPatientAPI:
    """Groups tests for the Patient API."""

    def test_list_patients_isolates_by_organization(self):
        # ...
        # ★ Update user creation
        user_a = User.objects.create_user(username='user_a', password='password123')
        UserProfile.objects.create(user=user_a, organization=org_a, role=UserProfile.Roles.DOCTOR)
        # ... rest of the test ...

    def test_create_patient_assigns_correct_organization(self):
        # ...
        # ★ Update user creation
        user_a = User.objects.create_user(username='user_a', password='password123')
        UserProfile.objects.create(user=user_a, organization=org_a, role=UserProfile.Roles.DOCTOR)
       

    def test_list_patients_isolates_by_organization(self):
        """Tests that a user from Org A can only see patients from Org A."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')
        user_a = User.objects.create_user(username='user_a', password='password123')
        UserProfile.objects.create(user=user_a, organization=org_a)
        Patient.objects.create(first_name='Peter', last_name='Pan', organization=org_a, date_of_birth='2010-01-01')
        Patient.objects.create(first_name='Wendy', last_name='Darling', organization=org_a, date_of_birth='2011-02-02')
        Patient.objects.create(first_name='Captain', last_name='Hook', organization=org_b, date_of_birth='1999-03-03')
        client = APIClient()
        client.force_authenticate(user=user_a)

        # Act
        response = client.get('/api/v1/clinical/patients/')

        # Assert
        assert response.status_code == 200
        assert response.data['count'] == 2 # This will now be correct

    def test_create_patient_assigns_correct_organization(self):
        """Tests that a new patient is automatically assigned to the creator's organization."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        user_a = User.objects.create_user(username='user_a', password='password123')
        UserProfile.objects.create(user=user_a, organization=org_a)
        client = APIClient()
        client.force_authenticate(user=user_a)
        patient_payload = {
            'first_name': 'Tinker',
            'last_name': 'Bell',
            'date_of_birth': '2000-01-01'
        }
        
        # Act
        response = client.post('/api/v1/clinical/patients/', patient_payload, format='json')

        # Assert
        assert response.status_code == 201
        new_patient = Patient.objects.get()
        assert new_patient.organization == org_a