# FILE: apps/inventory/tests/test_stock_check_api.py

import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch
from apps.inventory.models import Medication, MedicationStock

@pytest.mark.django_db
class TestStockCheckAPI:
    """Groups all tests for the custom Stock Check API."""

    def test_doctor_can_check_stock_in_own_org_branch(self):
        """
        Tests the "happy path": a doctor successfully checks stock for a
        medication in their own organization's branch.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        medication = Medication.objects.create(name='Paracetamol 500mg', organization=org)
        stock = MedicationStock.objects.create(medication=medication, branch=branch, quantity=150)

        doctor_user = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)

        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        # Construct the URL with query parameters
        url = f'/api/v1/inventory/stock-check/?branch_id={branch.id}&medication_name=Paracetamol'

        # 2. Act
        response = client.get(url)

        # 3. Assert
        assert response.status_code == 200
        assert response.data['status'] == 'In Stock'
        assert response.data['quantity'] == 150
        assert response.data['medication_name'] == 'Paracetamol 500mg'

    def test_check_for_out_of_stock_item_returns_404(self):
        """
        Tests that the API returns a 404 Not Found if the medication
        doesn't exist in the stock records for that branch.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        branch = Branch.objects.create(name='Main Branch', organization=org, city='Testville')
        doctor_user = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)
        
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        # Note: We do NOT create a stock record for "Aspirin"
        url = f'/api/v1/inventory/stock-check/?branch_id={branch.id}&medication_name=Aspirin'
        
        # 2. Act
        response = client.get(url)
        
        # 3. Assert
        assert response.status_code == 404
        assert response.data['status'] == 'Out of Stock or Medication Not Found'

    def test_cannot_check_stock_in_another_orgs_branch(self):
        """
        Tests the security rule: a doctor from Org A cannot check stock
        for a branch belonging to Org B.
        """
        # 1. Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')
        
        doctor_a = User.objects.create_user(username='doc_a', password='123')
        UserProfile.objects.create(user=doctor_a, organization=org_a, role=UserProfile.Roles.DOCTOR)
        
        # This branch belongs to the WRONG organization
        branch_b = Branch.objects.create(name='Branch B', organization=org_b, city='Otherville')
        medication_b = Medication.objects.create(name='Med B', organization=org_b)
        MedicationStock.objects.create(medication=medication_b, branch=branch_b, quantity=50)

        client = APIClient()
        client.force_authenticate(user=doctor_a)
        
        # We try to check stock in Branch B
        url = f'/api/v1/inventory/stock-check/?branch_id={branch_b.id}&medication_name=Med B'

        # 2. Act
        response = client.get(url)
        
        # 3. Assert
        # The security filter in the view should prevent the lookup and return a 404.
        assert response.status_code == 404
        
    def test_check_stock_with_missing_parameters_fails(self):
        """
        Tests that the API returns a 400 Bad Request if the required
        query parameters are not provided.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        doctor_user = User.objects.create_user(username='doc', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        # 2. Act
        response = client.get('/api/v1/inventory/stock-check/') # No query params
        
        # 3. Assert
        assert response.status_code == 400
        assert "query parameters are required" in response.data['error']
