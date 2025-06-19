import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch, Bed
from apps.clinical.models import Patient, Admission, Appointment, MedicalRecord
from datetime import datetime

@pytest.mark.django_db
class TestAdmissionAPI:
    """Groups tests for the Admission Management API."""

    def setup_method(self):
        """Setup common objects for tests."""
        self.client = APIClient()
        self.org = Organization.objects.create(name='Test Clinic')
        self.branch = Branch.objects.create(name='Main Branch', organization=self.org)
        
        self.doctor_user = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=self.doctor_user, organization=self.org, role=UserProfile.Roles.DOCTOR)
        
        self.patient = Patient.objects.create(organization=self.org, first_name='John', last_name='Doe', date_of_birth='1980-01-01')
        self.available_bed = Bed.objects.create(branch=self.branch, number='201', category=Bed.BedCategory.PRIVATE_ROOM, status=Bed.BedStatus.AVAILABLE, daily_charge=1000)
        self.occupied_bed = Bed.objects.create(branch=self.branch, number='202', category=Bed.BedCategory.PRIVATE_ROOM, status=Bed.BedStatus.OCCUPIED, daily_charge=1000)
        
        self.client.force_authenticate(user=self.doctor_user)

    def test_create_admission_succeeds_with_available_bed(self):
        """Tests that staff can successfully admit a patient to an available bed."""
        payload = {
            "patient": str(self.patient.id),
            "bed": str(self.available_bed.id),
            "notes": "Admitted for observation."
        }
        response = self.client.post('/api/v1/clinical/admissions/', payload, format='json')
        assert response.status_code == 201

    def test_create_admission_fails_with_occupied_bed(self):
        """Tests that the API prevents creating an admission for a bed that is already occupied."""
        payload = {
            "patient": str(self.patient.id),
            "bed": str(self.occupied_bed.id),
            "notes": "This should fail."
        }
        response = self.client.post('/api/v1/clinical/admissions/', payload, format='json')
        assert response.status_code == 400
        # ★-- The assertion is now more specific for our custom error format --★
        assert "This bed is not available" in str(response.data['error']['message'])

    def test_get_consolidated_admission_details(self):
        """Tests the custom summary view provides all the correct nested data."""
        admission = Admission.objects.create(patient=self.patient, bed=self.available_bed)
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor_user, branch=self.branch, start_time=datetime.now(), end_time=datetime.now())
        MedicalRecord.objects.create(appointment=appt, diagnosis="Initial Checkup")

        url = f'/api/v1/clinical/admissions/{admission.id}/details/'
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert 'medical_records' in response.data
        assert len(response.data['medical_records']) == 1
