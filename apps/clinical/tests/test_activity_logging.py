import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch, Bed
from apps.clinical.models import Patient, Admission, DailyRound
from apps.billing.models import Service, Charge

@pytest.mark.django_db
class TestActivityLoggingAPI:
    """Groups tests for the 'log-activity' custom action."""

    def test_log_activity_creates_round_and_charge(self):
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org)
        doctor = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='1980-01-01')
        bed = Bed.objects.create(branch=branch, number='101', status=Bed.BedStatus.OCCUPIED, daily_charge=500)
        admission = Admission.objects.create(patient=patient, bed=bed)
        
        doctor_visit_service = Service.objects.create(
            name="Doctor's Visit", organization=org, category=Service.ServiceCategory.CONSULTATION, price=250.00
        )
        
        client = APIClient()
        client.force_authenticate(user=doctor)
        
        payload = {
            "service_provided": str(doctor_visit_service.id),
            "notes": "Patient is responding well to treatment."
        }
        
        # This URL now points to our new standalone view.
        url = f'/api/v1/clinical/admissions/{admission.id}/log-activity/'

        # 2. Act
        response = client.post(url, payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert DailyRound.objects.count() == 1
        assert Charge.objects.count() == 1

