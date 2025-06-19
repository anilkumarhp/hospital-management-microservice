# apps/clinical/tests/test_documents_api.py
import pytest
import io
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings # This is the decorator we're using
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
from apps.clinical.models import Patient, PatientDocument

# The class itself is NOT decorated
@pytest.mark.django_db
class TestDocumentUploadAPI:
    """Groups tests for the Document Upload API."""

    # ★-- THE FIX: The decorator goes here, on the method --★
    @override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage')
    def test_doctor_can_upload_document_for_patient(self):
        """
        Tests that an authorized user can successfully upload a file for a patient
        in their organization.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        doctor_user = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='2000-01-01')

        client = APIClient()
        client.force_authenticate(user=doctor_user)

        test_file = SimpleUploadedFile(
            "report.pdf",
            b"This is the content of the test PDF.",
            content_type="application/pdf"
        )
        
        upload_payload = {
            'description': 'Initial blood work results',
            'file': test_file
        }
        
        url = f'/api/v1/clinical/patients/{patient.id}/documents/'

        # 2. Act
        response = client.post(url, upload_payload, format='multipart')

        # 3. Assert
        assert response.status_code == 201
        assert PatientDocument.objects.count() == 1
        new_document =PatientDocument.objects.get()
        assert new_document.patient == patient
        assert 'report.pdf' in new_document.file.name