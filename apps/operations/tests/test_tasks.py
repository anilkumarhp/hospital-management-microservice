# apps/operations/tests/test_tasks.py
import pytest
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from apps.operations.models import Organization, UserProfile, LeaveRequest, Branch
from apps.clinical.models import Patient, Appointment
from apps.operations.tasks import process_conflicts_for_single_leave # Import the task directly


@pytest.mark.django_db
def test_conflict_task_cancels_correct_appointments():
    """
    Unit test for the Celery task that processes leave conflicts.
    We call the task function directly to test its logic.
    """
    # 1. Arrange: Set up a complex scenario
    org = Organization.objects.create(name='Test Clinic')
    branch = Branch.objects.create(name='Main Branch', organization=org)
    doctor = User.objects.create_user(username='doc', password='123')
    doctor_profile = UserProfile.objects.create(user=doctor, organization=org, role=UserProfile.Roles.DOCTOR)
    patient = Patient.objects.create(organization=org, first_name='Test', last_name='Patient', date_of_birth='2000-01-01')

    leave_start = datetime(2025, 7, 4, 9, 0) # July 4th, 9 AM
    leave_end = datetime(2025, 7, 4, 17, 0)  # July 4th, 5 PM
    leave_request = LeaveRequest.objects.create(
        staff_profile=doctor_profile,
        start_datetime=leave_start,
        end_datetime=leave_end,
        status=LeaveRequest.LeaveStatus.APPROVED
    )

    # This appointment SHOULD be cancelled
    conflicting_appt = Appointment.objects.create(
        patient=patient, doctor=doctor, branch=branch,
        start_time=datetime(2025, 7, 4, 10, 0), # 10 AM is within the leave period
        end_time=datetime(2025, 7, 4, 10, 30),
        status=Appointment.AppointmentStatus.SCHEDULED
    )

    # This appointment should NOT be cancelled
    safe_appt = Appointment.objects.create(
        patient=patient, doctor=doctor, branch=branch,
        start_time=datetime(2025, 7, 5, 10, 0), # July 5th is outside the leave period
        end_time=datetime(2025, 7, 5, 10, 30),
        status=Appointment.AppointmentStatus.SCHEDULED
    )

    # 2. Act
    # We call the task function directly with the ID of the leave request.
    process_conflicts_for_single_leave(leave_request.id)

    # 3. Assert
    # Refresh the objects from the database to get their new state
    conflicting_appt.refresh_from_db()
    safe_appt.refresh_from_db()
    
    # Check that the conflicting appointment was cancelled
    assert conflicting_appt.status == Appointment.AppointmentStatus.CANCELLED
    
    # Crucially, check that the non-conflicting appointment was untouched
    assert safe_appt.status == Appointment.AppointmentStatus.SCHEDULED