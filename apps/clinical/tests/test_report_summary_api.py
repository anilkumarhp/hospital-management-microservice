# apps/clinical/tests/test_report_summary_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
from apps.clinical.models import Patient, PatientDocument

@pytest.mark.django_db
class TestReportSummaryAPI:
    """Groups all tests for the custom Patient Report Summary API."""

    def test_report_summary_groups_documents_correctly(self):
        """
        Tests the core logic: documents are correctly grouped into 'internal'
        and 'external' based on the uploader's organization.
        """
        # 1. Arrange
        # Create two different organizations
        clinic_a = Organization.objects.create(name='A-Star Clinic')
        lab_b = Organization.objects.create(name='B-Tech Labs')

        # Create a doctor for Clinic A, who will be viewing the report
        doctor_a = User.objects.create_user(username='doc_a', password='123')
        UserProfile.objects.create(user=doctor_a, organization=clinic_a, role=UserProfile.Roles.DOCTOR)
        
        # Create a lab technician for Lab B
        tech_b = User.objects.create_user(username='tech_b', password='123')
        UserProfile.objects.create(user=tech_b, organization=lab_b, role=UserProfile.Roles.DOCTOR) # Role doesn't matter here

        # Create a patient who belongs to Clinic A
        patient = Patient.objects.create(organization=clinic_a, first_name='Test', last_name='Patient', date_of_birth='1990-01-01')

        # Upload one document by the internal doctor (Doctor A)
        internal_doc = PatientDocument.objects.create(
            patient=patient, uploaded_by=doctor_a, description='Internal Checkup Notes'
        )

        # Upload another document by the external lab tech (Tech B)
        external_doc = PatientDocument.objects.create(
            patient=patient, uploaded_by=tech_b, description='External Blood Work'
        )
        
        # Authenticate as the doctor from Clinic A
        client = APIClient()
        client.force_authenticate(user=doctor_a)

        # 2. Act
        url = f'/api/v1/clinical/patients/{patient.id}/report-summary/'
        response = client.get(url)

        # 3. Assert
        assert response.status_code == 200
        
        # Check the internal reports
        assert len(response.data['internal_reports']) == 1
        assert response.data['internal_reports'][0]['description'] == 'Internal Checkup Notes'
        
        # Check the external reports
        # The key should be the name of the external organization
        assert 'B-Tech Labs' in response.data['external_reports']
        assert len(response.data['external_reports']['B-Tech Labs']) == 1
        assert response.data['external_reports']['B-Tech Labs'][0]['description'] == 'External Blood Work'

    def test_cannot_access_summary_for_patient_in_another_org(self):
        """
        Tests that a doctor from Org A cannot access the report summary for
        a patient who belongs to Org B.
        """
        # 1. Arrange
        clinic_a = Organization.objects.create(name='A-Star Clinic')
        hospital_b = Organization.objects.create(name='B-Grade Hospital')

        doctor_a = User.objects.create_user(username='doc_a', password='123')
        UserProfile.objects.create(user=doctor_a, organization=clinic_a, role=UserProfile.Roles.DOCTOR)
        
        # This patient belongs to the WRONG organization
        patient_b = Patient.objects.create(organization=hospital_b, first_name='Other', last_name='Patient', date_of_birth='1992-01-01')

        client = APIClient()
        client.force_authenticate(user=doctor_a)

        # 2. Act
        url = f'/api/v1/clinical/patients/{patient_b.id}/report-summary/'
        response = client.get(url)

        # 3. Assert
        # Our view's initial permission check should reject this immediately.
        assert response.status_code == 404
        assert response.data['error']['message'] == "Patient not found in your organization."

