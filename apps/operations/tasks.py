# apps/operations/tasks.py
from celery import shared_task
import json
from datetime import datetime, timedelta
from .models import UserInvite, LeaveRequest
from apps.clinical.models import Appointment
from django.contrib.auth.models import User

@shared_task
def publish_user_invited_event(invite_id):
    """
    Fetches an invite and "publishes" an event for the notification service.
    """
    try:
        invite = UserInvite.objects.get(id=invite_id)

        # This is the data structure our Notification microservice will expect.
        event_data = {
            "event_type": "USER_INVITED",
            "payload": {
                "invite_id": str(invite.id),
                "email_to": invite.email,
                "organization_name": invite.organization.name,
                "role": invite.role,
                "invite_token": str(invite.token),
                "expires_at": invite.expires_at.isoformat()
            }
        }

        # For now, instead of connecting to a real SQS queue,
        # we will just print the event. This proves the entire flow works.
        print("--- PUBLISHING NOTIFICATION EVENT ---")
        print(json.dumps(event_data, indent=2))
        print("------------------------------------")

        return "Event published successfully"
    except UserInvite.DoesNotExist:
        return "Invite not found."
    

@shared_task
def process_conflicts_for_single_leave(leave_request_id):
    """
    A task triggered immediately when a single leave request is approved.
    It finds and cancels all conflicting appointments for that specific leave.
    """
    try:
        leave = LeaveRequest.objects.get(id=leave_request_id)
    except LeaveRequest.DoesNotExist:
        print(f"Error: Could not find LeaveRequest with id {leave_request_id}")
        return
        
    print(f"--- [Immediate Task] Processing leave for {leave.staff_profile.user.username} ---")

    # Find all scheduled appointments that fall within this specific leave period
    conflicting_appointments = Appointment.objects.filter(
        doctor=leave.staff_profile.user,
        status=Appointment.AppointmentStatus.SCHEDULED,
        start_time__gte=leave.start_datetime,
        start_time__lte=leave.end_datetime
    )

    for appt in conflicting_appointments:
        # 1. Update the appointment status
        appt.status = Appointment.AppointmentStatus.CANCELLED
        appt.save()
        
        # 2. Find the patient's contact email (logic is the same as the periodic task)
        patient_email = None
        if appt.patient.external_user_id:
            try:
                patient_user = User.objects.get(id=appt.patient.external_user_id)
                patient_email = patient_user.email
            except User.DoesNotExist:
                pass # Silently fail if patient user not found
        
        # 3. Publish an event for the notification service
        event_data = {
            "event_type": "APPOINTMENT_CANCELLED_STAFF_UNAVAILABLE",
            "payload": { "appointment_id": str(appt.id), "patient_contact_email": patient_email }
        }
        print(f"--- PUBLISHING CANCELLATION EVENT for Appointment {appt.id} ---")
        print(json.dumps(event_data, indent=2))
        print("---------------------------------------------------------")
        
    print(f"Processed {conflicting_appointments.count()} conflicts for leave {leave_request_id}.")


@shared_task
def check_for_appointment_conflicts_and_notify():
    """
    This periodic task now acts as a safety net. Its logic remains the same,
    but we might run it less frequently (e.g., once a day).
    """
    # ... (The code for this task from the previous Canvas remains unchanged) ...
    print(f"--- [Periodic Task] Running conflict check at {datetime.now()} ---")
    
    one_hour_ago = datetime.now() - timedelta(hours=1)