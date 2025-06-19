from rest_framework import serializers
from .models import Service
from .models import Service, Charge, Invoice
from apps.clinical.serializers import PatientSerializer

class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Service model, used by admins to manage
    their organization's service catalog.
    """
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'category', 'price', 'is_active'
        ]
        # The 'organization' field is handled automatically by the view,
        # so we don't include it here for user input.


class InvoiceSerializer(serializers.ModelSerializer):
    """A detailed serializer for viewing a generated invoice."""
    # Nest the patient and charge details for a complete view.
    patient = PatientSerializer(read_only=True)
    charges = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'patient', 'organization', 'start_date', 'end_date',
            'total_amount', 'status', 'created_at', 'charges'
        ]