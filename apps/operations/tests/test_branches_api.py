# apps/operations/tests/test_branches_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch

@pytest.mark.django_db
class TestBranchAPI:
    """Groups tests for the Branch API."""

    def test_list_branches_succeeds_for_admin(self):
        """Tests that a user with an ADMIN role can see branches from their org."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')

        # Create an ADMIN user for Org A
        admin_user = User.objects.create_user(username='admin_a', password='password123')
        UserProfile.objects.create(user=admin_user, organization=org_a, role=UserProfile.Roles.ADMIN)

        Branch.objects.create(name='Main St Clinic', organization=org_a, city='City A')
        Branch.objects.create(name='Downtown Clinic', organization=org_a, city='City A')
        Branch.objects.create(name='General Hospital', organization=org_b, city='City B')

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Act
        response = client.get('/api/v1/operations/branches/')

        # Assert
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_list_branches_fails_for_doctor(self):
        """Tests that a non-admin (e.g., a Doctor) cannot list branches."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        doctor_user = User.objects.create_user(username='doctor_a', password='password123')
        UserProfile.objects.create(user=doctor_user, organization=org_a, role=UserProfile.Roles.DOCTOR)
        
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        # Act
        response = client.get('/api/v1/operations/branches/')

        # Assert
        assert response.status_code == 403 # Forbidden!

    def test_create_branch_by_admin_succeeds(self):
        """Tests that a user with an ADMIN role can create a branch."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        admin_user = User.objects.create_user(username='admin_a', password='password123')
        UserProfile.objects.create(user=admin_user, organization=org_a, role=UserProfile.Roles.ADMIN)

        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        # ★-- FIX for ERROR --★
        # This payload was missing in the new test functions.
        branch_payload = {
            'name': 'Uptown Clinic',
            'address_line_1': '123 Test Ave',
            'city': 'City A',
        }
        
        # Act
        response = client.post('/api/v1/operations/branches/', branch_payload, format='json')

        # Assert
        assert response.status_code == 201
        new_branch = Branch.objects.get()
        assert new_branch.name == 'Uptown Clinic'
        assert new_branch.organization == org_a

    def test_create_branch_by_doctor_fails(self):
        """Tests that a non-admin (e.g., a Doctor) cannot create a branch."""
        # Arrange
        org_a = Organization.objects.create(name='Clinic A')
        doctor_user = User.objects.create_user(username='doctor_a', password='password123')
        UserProfile.objects.create(user=doctor_user, organization=org_a, role=UserProfile.Roles.DOCTOR)
        
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        # ★-- FIX for ERROR --★
        # This payload was also missing.
        branch_payload = {
            'name': 'Secret Clinic',
            'address_line_1': '456 Hideaway Rd',
            'city': 'City A'
        }

        # Act
        response = client.post('/api/v1/operations/branches/', branch_payload, format='json')

        # Assert
        assert response.status_code == 403 # Forbidden!