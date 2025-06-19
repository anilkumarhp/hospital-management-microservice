import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
from apps.clinical.models import Patient
from apps.billing.models import Service, Charge, Invoice
from datetime import date

@pytest.mark.django_db
class TestInvoiceGeneration:
    """Groups tests for the custom GenerateInvoiceView."""

    def test_generate_invoice_collects_unbilled_charges(self):
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        admin = User.objects.create_user(username='admin', password='123')
        UserProfile.objects.create(user=admin, organization=org, role=UserProfile.Roles.ADMIN)
        patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='1980-01-01')
        
        service1 = Service.objects.create(name="Svc 1", organization=org, price=100)
        service2 = Service.objects.create(name="Svc 2", organization=org, price=50)

        # Create two charges that should be on the invoice
        charge1 = Charge.objects.create(patient=patient, service=service1, quantity=1)
        charge2 = Charge.objects.create(patient=patient, service=service2, quantity=2) # Total: 100
        
        # Create a charge that is already on another invoice
        old_invoice = Invoice.objects.create(patient=patient, organization=org, start_date=date(2024,1,1), end_date=date(2024,1,1))
        Charge.objects.create(patient=patient, service=service1, quantity=1, invoice=old_invoice)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        payload = {
            "patient_id": str(patient.id),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31"
        }

        # 2. Act
        response = client.post('/api/v1/billing/generate-invoice/', payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert Invoice.objects.count() == 2 # The old one plus our new one
        
        new_invoice = Invoice.objects.get(id=response.data['id'])
        # Total should be 100 (for charge1) + 50*2 (for charge2) = 200
        assert new_invoice.total_amount == 200.00
        assert new_invoice.charges.count() == 2
        
        # Verify the charges were updated
        charge1.refresh_from_db()
        assert charge1.invoice == new_invoice