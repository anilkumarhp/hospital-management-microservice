
from rest_framework import serializers
from .models import Medication, MedicationStock
from apps.operations.models import Branch

class MedicationSerializer(serializers.ModelSerializer):
    """Serializer for the Medication catalog."""
    class Meta:
        model = Medication
        fields = ['id', 'name', 'description']
        # 'organization' is set automatically by the view.

class MedicationStockSerializer(serializers.ModelSerializer):
    """Serializer for managing stock levels at a branch."""
    
    # On GET requests, show the names for better readability.
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    # On POST/PUT requests, expect the IDs.
    medication = serializers.PrimaryKeyRelatedField(queryset=Medication.objects.all())
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())

    class Meta:
        model = MedicationStock
        fields = [
            'id', 'medication', 'medication_name', 'branch', 'branch_name', 
            'quantity', 'reorder_level', 'last_updated'
        ]
        read_only_fields = ['last_updated']

    def validate(self, data):
        """
        Custom validation to ensure the branch and medication belong to the
        same organization as the user.
        """
        request_user = self.context['request'].user
        user_org = request_user.profile.organization

        if data['branch'].organization != user_org:
            raise serializers.ValidationError("This branch does not belong to your organization.")
        
        if data['medication'].organization != user_org:
            raise serializers.ValidationError("This medication does not belong to your organization.")
            
        return data
