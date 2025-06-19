# FILE: apps/inventory/tests/test_inventory_api.py

import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch
from apps.inventory.models import Medication, MedicationStock

@pytest.mark.django_db
class TestInventoryAPI:
    """Groups all tests for the Inventory Management APIs."""

    def test_admin_can_manage_medication_catalog(self):
        """
        Tests that an ADMIN can create and list medications for their organization.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        admin_user = User.objects.create_user(username='admin', password='123')
        UserProfile.objects.create(user=admin_user, organization=org, role=UserProfile.Roles.ADMIN)

        client = APIClient()
        client.force_authenticate(user=admin_user)

        medication_payload = {
            "name": "Paracetamol 500mg",
            "description": "Standard pain reliever."
        }

        # 2. Act (Create)
        create_response = client.post('/api/v1/inventory/medications/', medication_payload, format='json')

        # 3. Assert (Create)
        assert create_response.status_code == 201
        assert Medication.objects.count() == 1
        new_med = Medication.objects.get()
        assert new_med.name == "Paracetamol 500mg"
        assert new_med.organization == org

        # 4. Act (List)
        list_response = client.get('/api/v1/inventory/medications/')
        
        # 5. Assert (List)
        assert list_response.status_code == 200
        assert list_response.data['count'] == 1

    def test_doctor_cannot_manage_medication_catalog(self):
        """
        Tests that a non-ADMIN (e.g., Doctor) is forbidden from managing the catalog.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        doctor_user = User.objects.create_user(username='doctor', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)

        client = APIClient()
        client.force_authenticate(user=doctor_user)

        payload = {"name": "Unauthorized Med"}

        # 2. Act
        response = client.post('/api/v1/inventory/medications/', payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden


    def test_admin_can_manage_stock_levels(self):
        """
        Tests that an ADMIN can create and list stock records for their organization.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        medication = Medication.objects.create(name='Amoxicillin', organization=org)
        
        admin_user = User.objects.create_user(username='admin', password='123')
        UserProfile.objects.create(user=admin_user, organization=org, role=UserProfile.Roles.ADMIN)

        client = APIClient()
        client.force_authenticate(user=admin_user)

        stock_payload = {
            "medication": medication.id,
            "branch": branch.id,
            "quantity": 200
        }

        # 2. Act (Create)
        create_response = client.post('/api/v1/inventory/stocks/', stock_payload, format='json')

        # 3. Assert (Create)
        assert create_response.status_code == 201
        assert MedicationStock.objects.count() == 1
        new_stock = MedicationStock.objects.get()
        assert new_stock.branch == branch
        assert new_stock.medication == medication
        assert new_stock.quantity == 200

    def test_cannot_create_stock_for_branch_in_another_org(self):
        """
        Tests that the validation prevents creating a stock record for a branch
        that does not belong to the user's organization.
        """
        # 1. Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')
        
        admin_a = User.objects.create_user(username='admin_a', password='123')
        UserProfile.objects.create(user=admin_a, organization=org_a, role=UserProfile.Roles.ADMIN)

        medication_a = Medication.objects.create(name='Med A', organization=org_a)
        # This branch belongs to the WRONG organization
        branch_b = Branch.objects.create(name='Branch B', organization=org_b, city='Otherville')

        client = APIClient()
        client.force_authenticate(user=admin_a)

        payload = {
            "medication": medication_a.id,
            "branch": branch_b.id,
            "quantity": 100
        }

        # 2. Act
        response = client.post('/api/v1/inventory/stocks/', payload, format='json')

        # 3. Assert
        assert response.status_code == 400 # Bad Request
        assert "This branch does not belong to your organization" in str(response.data)

