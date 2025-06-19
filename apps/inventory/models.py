# apps/inventory/models.py
import uuid
from django.db import models
from apps.operations.models import Organization, Branch

class Medication(models.Model):
    """
    Represents a type of medication in the master catalog for an organization.
    e.g., "Paracetamol 500mg", "Amoxicillin 250mg"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="medications")
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_medication_for_organization')
        ]

    def __str__(self):
        return self.name


class MedicationStock(models.Model):
    """
    Tracks the stock level of a specific Medication at a specific Branch.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # The specific medication we are tracking
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="stock_levels")
    
    # The specific branch where this stock is located
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="medication_stocks")
    
    quantity = models.PositiveIntegerField(default=0, help_text="The current number of units in stock.")
    
    # Useful for reordering, e.g., "Notify when quantity falls below this level."
    reorder_level = models.PositiveIntegerField(default=10)
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        # A medication can only have one stock record per branch.
        constraints = [
            models.UniqueConstraint(fields=['medication', 'branch'], name='unique_stock_item_per_branch')
        ]

    def __str__(self):
        return f"{self.medication.name} at {self.branch.name}: {self.quantity}"
