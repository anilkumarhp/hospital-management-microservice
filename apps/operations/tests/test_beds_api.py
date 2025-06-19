import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch, Bed

@pytest.mark.django_db
class TestBedAPI:
    """Groups tests for the Bed Management API."""

    def setup_method(self):
        """A setup method called before each test in this class."""
        self.client = APIClient()
        self.org_a = Organization.objects.create(name='Clinic A')
        self.org_b = Organization.objects.create(name='Hospital B')

        self.admin_a = User.objects.create_user(username='admin_a', password='123')
        UserProfile.objects.create(user=self.admin_a, organization=self.org_a, role=UserProfile.Roles.ADMIN)

        self.branch_a1 = Branch.objects.create(name='Branch A1', organization=self.org_a)
        self.branch_b1 = Branch.objects.create(name='Branch B1', organization=self.org_b)

        Bed.objects.create(branch=self.branch_a1, number='101', category=Bed.BedCategory.PRIVATE_ROOM, status=Bed.BedStatus.AVAILABLE, daily_charge=500)
        Bed.objects.create(branch=self.branch_a1, number='102', category=Bed.BedCategory.PRIVATE_ROOM, status=Bed.BedStatus.OCCUPIED, daily_charge=500)
        Bed.objects.create(branch=self.branch_b1, number='B-101', category=Bed.BedCategory.GENERAL_WARD, status=Bed.BedStatus.AVAILABLE, daily_charge=100)

    def test_admin_can_list_and_filter_beds_in_own_org(self):
        """
        Tests that an admin can list beds from their own organization and that
        filtering by status works correctly.
        """
        # 1. Arrange
        self.client.force_authenticate(user=self.admin_a)

        # 2. Act
        # First, get all beds in the organization
        all_response = self.client.get('/api/v1/operations/beds/')
        
        # Then, get only the available beds
        available_response = self.client.get('/api/v1/operations/beds/?status=AVAILABLE')

        # 3. Assert
        assert all_response.status_code == 200
        # Admin from Org A should only see the 2 beds from their org
        assert all_response.data['count'] == 2

        assert available_response.status_code == 200
        # The filtered list should only contain the 1 available bed
        assert available_response.data['count'] == 1
        assert available_response.data['results'][0]['number'] == '101'