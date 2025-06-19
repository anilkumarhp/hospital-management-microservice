# apps/clinical/models.py
import uuid
from django.db import models
from apps.operations.models import Organization
from apps.operations.models import Branch
from django.contrib.auth.models import User

class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_user_id = models.UUIDField(unique=True, db_index=True, null=True, blank=True)
    
    # ★-- THIS IS THE CRUCIAL LINE --★
    # Make sure this line exists and is correct.
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="patients")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    

class Appointment(models.Model):
    class AppointmentStatus(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- Relationships ---
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    
    # We link to Django's User model, but limit choices to users with the DOCTOR role
    # This provides a nice dropdown in the Django admin.
    doctor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # If doctor's account is deleted, don't delete the appointment record
        null=True,
        related_name="appointments",
        limit_choices_to={'profile__role': 'DOCTOR'}
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="appointments")

    # --- Appointment Details ---
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
        db_index=True # We will often filter by status
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Appointment for {self.patient} with Dr. {self.doctor.last_name} at {self.start_time}"
    

class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # A OneToOneField ensures that one appointment can have exactly ONE medical record.
    # This is a stronger relationship than a ForeignKey.
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="medical_record")
    
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Medical Record for Appointment {self.appointment.id}"

# ★-- ADD NEW MODEL: Prescription --★
class Prescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # A ForeignKey means one Medical Record can have MANY prescriptions.
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="prescriptions")

    medication = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100) # e.g., "500mg", "1 tablet"
    frequency = models.CharField(max_length=100) # e.g., "Twice a day", "As needed"
    duration_days = models.PositiveIntegerField(help_text="Duration of the prescription in days.")

    def __str__(self):
        return f"{self.medication} ({self.dosage})"
    
def patient_directory_path(instance, filename):
    # This path logic is good, it separates files by patient
    return f'patients/{instance.patient.id}/documents/{filename}'

# ★-- RENAME THIS CLASS and add the 'document_type' field --★
class PatientDocument(models.Model):
    class DocumentType(models.TextChoices):
        LAB_REPORT = 'LAB_REPORT', 'Lab Report'
        PRESCRIPTION = 'PRESCRIPTION', 'Prescription'
        IMAGING_SCAN = 'IMAGING_SCAN', 'Imaging Scan'
        INSURANCE = 'INSURANCE', 'Insurance Card'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="uploaded_documents")
    
    # We add a type to categorize the document
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    
    file = models.FileField(upload_to=patient_directory_path)
    description = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ★-- NEW: Order by most recent first --★
        ordering = ['-uploaded_at']

       
class Admission(models.Model):
    """Tracks a patient's admission to a bed in a branch."""
    class AdmissionStatus(models.TextChoices):
        ADMITTED = 'ADMITTED', 'Admitted'
        DISCHARGED = 'DISCHARGED', 'Discharged'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="admissions")
    bed = models.ForeignKey('operations.Bed', on_delete=models.PROTECT, related_name="admissions")
    
    admitted_at = models.DateTimeField(auto_now_add=True)
    discharged_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=AdmissionStatus.choices, default=AdmissionStatus.ADMITTED, db_index=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Admission for {self.patient} to Bed {self.bed.number}"
    

class DailyRound(models.Model):
    """
    Records a single interaction (e.g., a doctor's visit, a nurse's check-in)
    during a specific patient admission.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="daily_rounds")
    service_provided = models.ForeignKey('billing.Service', on_delete=models.PROTECT, null=True, blank=True)
  
    # The staff member who performed the action.
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="daily_rounds_performed")
    
    # The associated charge for this activity (e.g., "Doctor Visit Fee"). Optional.
    charge = models.OneToOneField('billing.Charge', on_delete=models.SET_NULL, null=True, blank=True)
    
    notes = models.TextField()
    round_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Round for Admission {self.admission.id} at {self.round_time}"