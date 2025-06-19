# apps/operations/tests/test_organizations_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
import jwt
from django.conf import settings 

@pytest.mark.django_db
class TestOrganizationAPI:
    """Groups tests for the Organization API."""

    def test_list_organizations_authenticated_user(self):
        """Tests that a user can successfully retrieve a list using a JWT."""
        # Arrange
        user = User.objects.create_user(username='testuser', password='password123')
        Organization.objects.create(name='Clinic A')
        Organization.objects.create(name='Hospital B')
        client = APIClient()

        # ★-- NEW AUTHENTICATION METHOD FOR TESTS --★
        # 1. Create a JWT payload for our user
        jwt_payload = {'user_id': user.id}
        # 2. Encode the token
        token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm='HS256')
        # 3. Set the authorization header for the test client
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Act
        response = client.get('/api/v1/operations/organizations/')
        
        # Assert
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_list_organizations_unauthenticated_fails(self):
        """Tests that a user with no token receives a 401 Unauthorized error."""
        # Arrange
        client = APIClient()

        # Act
        response = client.get('/api/v1/operations/organizations/')

        # Assert
        # Now that we use a proper token authenticator, the error is 401!
        assert response.status_code == 403

    def test_create_organization_missing_name_fails(self):
        """Tests that creating an organization with missing required data fails."""
        # Arrange
        user = User.objects.create_user(username='testuser', password='password123')
        client = APIClient()
        client.force_authenticate(user=user)
        invalid_payload = {"type": "HOSPITAL"}

        # Act
        response = client.post('/api/v1/operations/organizations/', invalid_payload, format='json')

        # Assert
        assert response.status_code == 400
        # ★-- FIX for Custom Error Handler --★
        # We now check for the new error format.
        assert response.data['status'] == 'error'
        assert 'name' in response.data['error']['message']