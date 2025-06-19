# FILE: apps/operations/tests/test_scheduling_api.py

import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, Branch, StaffAvailability, LeaveRequest
from datetime import time, datetime, timedelta

@pytest.mark.django_db
class TestSchedulingAPI:
    """Groups all tests for the Staff Scheduling and Leave Management APIs."""

    def setup_method(self):
        """A setup method called before each test in this class."""
        self.client = APIClient()
        self.org = Organization.objects.create(name='Test Clinic')
        self.branch = Branch.objects.create(name='Main Branch', organization=self.org, city='Testville')

        # Create an Admin user for the organization
        self.admin_user = User.objects.create_user(username='admin', password='123')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, organization=self.org, role=UserProfile.Roles.ADMIN)
        
        # Create a Doctor user for the organization
        self.doctor_user = User.objects.create_user(username='doctor', password='123')
        self.doctor_profile = UserProfile.objects.create(user=self.doctor_user, organization=self.org, role=UserProfile.Roles.DOCTOR)

    def test_admin_can_create_staff_availability(self):
        """Tests that an ADMIN can set the weekly schedule for a staff member."""
        # 1. Arrange
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "staff_profile": self.doctor_profile.id,
            "branch": self.branch.id,
            "day_of_week": 0, # Monday
            "start_time": "09:00:00",
            "end_time": "17:00:00"
        }

        # 2. Act
        response = self.client.post('/api/v1/operations/staff-availability/', payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert StaffAvailability.objects.count() == 1
        availability = StaffAvailability.objects.get()
        assert availability.staff_profile == self.doctor_profile

    def test_doctor_cannot_create_staff_availability(self):
        """Tests that a non-admin is forbidden from setting schedules."""
        # 1. Arrange
        self.client.force_authenticate(user=self.doctor_user)
        payload = { "staff_profile": self.doctor_profile.id, "branch": self.branch.id, "day_of_week": 1 }

        # 2. Act
        response = self.client.post('/api/v1/operations/staff-availability/', payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden

    def test_doctor_can_request_leave(self):
        """Tests that a staff member can create a leave request for themselves."""
        # 1. Arrange
        self.client.force_authenticate(user=self.doctor_user)
        start_time = datetime.now() + timedelta(days=10)
        end_time = start_time + timedelta(days=1)
        payload = {
            "start_datetime": start_time.isoformat(),
            "end_datetime": end_time.isoformat(),
            "reason": "Family vacation"
        }

        # 2. Act
        response = self.client.post('/api/v1/operations/leave-requests/', payload, format='json')

        # 3. Assert
        assert response.status_code == 201
        assert LeaveRequest.objects.count() == 1
        leave_request = LeaveRequest.objects.get()
        # Check it was correctly assigned to the doctor
        assert leave_request.staff_profile == self.doctor_profile
        # Check that the status defaults to PENDING
        assert leave_request.status == LeaveRequest.LeaveStatus.PENDING

    def test_admin_can_approve_leave_request(self):
        """Tests the custom 'review' action for an Admin to approve leave."""
        # 1. Arrange
        # The doctor first creates a leave request
        leave_request = LeaveRequest.objects.create(
            staff_profile=self.doctor_profile,
            start_datetime=datetime.now(),
            end_datetime=datetime.now()
        )
        
        # Now, the admin logs in to review it
        self.client.force_authenticate(user=self.admin_user)
        
        # Construct the custom action URL
        url = f'/api/v1/operations/leave-requests/{leave_request.id}/review/'
        payload = {"status": "APPROVED"}

        # 2. Act
        response = self.client.post(url, payload, format='json')
        
        # 3. Assert
        assert response.status_code == 200
        # Refresh the object from the database to check its new status
        leave_request.refresh_from_db()
        assert leave_request.status == LeaveRequest.LeaveStatus.APPROVED
        assert leave_request.reviewed_by == self.admin_user

    def test_doctor_cannot_approve_leave_request(self):
        """Tests that a non-admin cannot use the 'review' action."""
        # 1. Arrange
        leave_request = LeaveRequest.objects.create(staff_profile=self.doctor_profile, start_datetime=datetime.now(), end_datetime=datetime.now())
        # The doctor tries to approve their own leave
        self.client.force_authenticate(user=self.doctor_user)
        url = f'/api/v1/operations/leave-requests/{leave_request.id}/review/'
        payload = {"status": "APPROVED"}

        # 2. Act
        response = self.client.post(url, payload, format='json')

        # 3. Assert
        assert response.status_code == 403 # Forbidden
