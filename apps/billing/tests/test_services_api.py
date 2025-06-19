# apps/billing/tests/test_services_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile
from apps.billing.models import Service

@pytest.mark.django_db
class TestServiceAPI:
    """Groups tests for the Service catalog API."""

    def test_admin_can_create_service(self):
        """
        Tests that a user with an ADMIN role can create a new service,
        and it's correctly assigned to their organization.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        admin_user = User.objects.create_user(username='admin', password='123')
        UserProfile.objects.create(user=admin_user, organization=org, role=UserProfile.Roles.ADMIN)

        client = APIClient()
        client.force_authenticate(user=admin_user)

        service_payload = {
            "name": "Standard Consultation",
            "category": Service.ServiceCategory.CONSULTATION,
            "price": "150.00"
        }

        # 2. Act
        response = client.post('/api/v1/billing/services/', service_payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert Service.objects.count() == 1
        new_service = Service.objects.get()
        assert new_service.name == "Standard Consultation"
        assert new_service.organization == org

    def test_doctor_cannot_create_service(self):
        """
        Tests that a non-admin user (e.g., a Doctor) is forbidden
        from creating a new service.
        """
        # 1. Arrange
        org = Organization.objects.create(name='Test Clinic')
        doctor_user = User.objects.create_user(username='doctor', password='123')
        UserProfile.objects.create(user=doctor_user, organization=org, role=UserProfile.Roles.DOCTOR)

        client = APIClient()
        client.force_authenticate(user=doctor_user)

        service_payload = {
            "name": "Unauthorized Service",
            "category": Service.ServiceCategory.OTHER,
            "price": "99.99"
        }

        # 2. Act
        response = client.post('/api/v1/billing/services/', service_payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden

    def test_admin_can_list_only_own_org_services(self):
        """
        Tests that the API list view is correctly filtered and only shows
        services from the user's own organization.
        """
        # 1. Arrange
        org_a = Organization.objects.create(name='Clinic A')
        org_b = Organization.objects.create(name='Hospital B')

        admin_a = User.objects.create_user(username='admin_a', password='123')
        UserProfile.objects.create(user=admin_a, organization=org_a, role=UserProfile.Roles.ADMIN)

        # Create services for both organizations
        Service.objects.create(name='Consult A', organization=org_a, price=100)
        Service.objects.create(name='Procedure A', organization=org_a, price=200)
        Service.objects.create(name='Consult B', organization=org_b, price=150) # This should not be visible

        client = APIClient()
        client.force_authenticate(user=admin_a)

        # 2. Act
        response = client.get('/api/v1/billing/services/')

        # 3. Assert
        assert response.status_code == 200
        assert response.data['count'] == 2 # Should only see the 2 services from Org A
        
        response_names = {s['name'] for s in response.data['results']}
        assert response_names == {'Consult A', 'Procedure A'}
