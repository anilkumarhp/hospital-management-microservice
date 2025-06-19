from rest_framework import serializers
from .models import Organization, Branch, UserInvite, StaffAvailability, LeaveRequest, Bed


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "type", "created_at"]


class BranchSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'organization', 'organization_name', 'address_line_1', 'city'
        ]
        # ★-- THE REAL FIX --★
        # Just like with the Patient serializer, we tell DRF that the 'organization'
        # is for display only and should not be expected on input. The view will provide it.
        read_only_fields = ['organization', 'organization_name']


class UserInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInvite
        # We only need email and role as input from the admin.
        # Everything else will be set by the system.
        fields = ['email', 'role']


class StaffAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for managing a staff member's weekly availability."""
    class Meta:
        model = StaffAvailability
        fields = ['id', 'staff_profile', 'branch', 'day_of_week', 'start_time', 'end_time']

class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for staff to request and view leave."""
    staff_profile = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'staff_profile', 'start_datetime', 'end_datetime', 
            'reason', 'status', 'reviewed_by'
        ]
        read_only_fields = ['status', 'reviewed_by']


class BedSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    class Meta:
        model = Bed
        # ★-- UPDATED FIELDS --★
        fields = [
            'id', 'branch_name', 'building', 'floor_number', 'block_number', 
            'number', 'category', 'status', 'daily_charge'
        ]