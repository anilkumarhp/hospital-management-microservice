from celery import shared_task
from django.utils import timezone
from .models import Charge, Service
from apps.clinical.models import Admission

@shared_task
def create_daily_bed_charges():
    """
    A periodic task that runs daily to create charges for all admitted patients.
    """
    # Find all currently admitted patients
    active_admissions = Admission.objects.filter(status=Admission.AdmissionStatus.ADMITTED)
    
    for admission in active_admissions:
        bed = admission.bed
        patient = admission.patient
        
        # Create a charge for the daily bed fee
        Charge.objects.create(
            patient=patient,
            # We assume a "Bed Charge" service exists for the bed's category
            # A more robust system would link Bed -> Service directly
            service_name=f"{bed.get_category_display()} Charge", # This part needs a real Service object
            quantity=1,
            price_at_charge=bed.daily_charge
        )
    print(f"Created daily bed charges for {active_admissions.count()} patients.")
