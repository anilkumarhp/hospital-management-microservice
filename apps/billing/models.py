from django.db import models

# Create your models here.
# apps/billing/models.py
import uuid
from django.db import models
from apps.operations.models import Organization
from apps.clinical.models import Patient

class Service(models.Model):
    """
    Represents a billable service offered by an organization.
    e.g., "Standard Consultation", "X-Ray", "Paracetamol (10-strip)"
    """
    class ServiceCategory(models.TextChoices):
        CONSULTATION = 'CONSULTATION', 'Consultation'
        PROCEDURE = 'PROCEDURE', 'Procedure'
        LAB_TEST = 'LAB_TEST', 'Lab Test'
        MEDICATION = 'MEDICATION', 'Medication'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="services")
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=ServiceCategory.choices, db_index=True)
    
    # We use DecimalField for money. It's precise and avoids floating-point errors.
    # max_digits is the total number of digits, decimal_places is the number after the decimal.
    price = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['category', 'name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_service_for_organization')
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Invoice(models.Model):
    """
    Represents a collection of charges for a patient over a specific period.
    This is the final bill presented to the patient.
    """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        FINALIZED = 'FINALIZED', 'Finalized'
        PAID = 'PAID', 'Paid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="invoices")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="invoices")

    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice for {self.patient} from {self.start_date} to {self.end_date}"


class BillingConfiguration(models.Model):
    class BedChargingCycle(models.TextChoices):
        FROM_ADMISSION_TIME = '24_HOUR_CYCLE', '24-Hour Cycle (from admission time)'
        CALENDAR_DAY = 'CALENDAR_DAY', 'Calendar Day (midnight to midnight)'

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    bed_charging_cycle = models.CharField(max_length=20, choices=BedChargingCycle.choices)
    # We could add other settings here, like tax rates, etc.


class Charge(models.Model):
    """
    Represents a single charge for a service rendered to a patient.
    """
    class ChargeStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="charges")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="charges")
    
    quantity = models.PositiveIntegerField(default=1)
    
    # Allow this to be null initially; we will set it in the save method.
    price_at_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=10, choices=ChargeStatus.choices, default=ChargeStatus.PENDING, db_index=True)
    billed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-billed_at']
    
    def save(self, *args, **kwargs):
        """
        Custom save method to automatically set prices.
        """
        # If the price for this charge hasn't been set, set it from the
        # linked service's current price. This is robust and safe.
        if self.price_at_charge is None:
            self.price_at_charge = self.service.price
        
        # Always recalculate the total price before saving.
        self.total_price = self.price_at_charge * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Charge for {self.patient} - {self.service.name} ({self.total_price})"

