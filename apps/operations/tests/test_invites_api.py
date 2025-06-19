# apps/operations/tests/test_invites_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, UserInvite

@pytest.mark.django_db
class TestInviteAPI:
    """Groups tests for the User Invitation API."""

    def test_admin_can_create_invite(self):
        """Tests that an ADMIN can successfully create an invitation."""
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        admin_user = User.objects.create_user(username='admin_user', password='password123')
        UserProfile.objects.create(user=admin_user, organization=org, role=UserProfile.Roles.ADMIN)

        client = APIClient()
        client.force_authenticate(user=admin_user)

        invite_payload = {
            "email": "new.doctor@example.com",
            "role": UserProfile.Roles.DOCTOR
        }

        # 2. Act
        response = client.post('/api/v1/operations/invites/', invite_payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert UserInvite.objects.count() == 1
        new_invite = UserInvite.objects.get()
        assert new_invite.email == "new.doctor@example.com"
        assert new_invite.organization == org
        assert new_invite.role == UserProfile.Roles.DOCTOR

    def test_doctor_cannot_create_invite(self):
        """Tests that a non-ADMIN (e.g., a Doctor) is forbidden from creating an invite."""
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        doctor_user = User.objects.create_user(username='doctor_user', password='password123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)

        client = APIClient()
        client.force_authenticate(user=doctor_user)

        invite_payload = {
            "email": "another.doctor@example.com",
            "role": UserProfile.Roles.DOCTOR
        }

        # 2. Act
        response = client.post('/api/v1/operations/invites/', invite_payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden!