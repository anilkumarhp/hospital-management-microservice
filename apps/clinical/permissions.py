# apps/clinical/permissions.py
from rest_framework import permissions

class IsPatientSelf(permissions.BasePermission):
    """
    Permission to only allow patients to view their own data.
    """
    def has_permission(self, request, view):
        # We start by ensuring the user is logged in and is not staff.
        # This prevents doctors/admins from using patient-portal endpoints.
        return request.user and request.user.is_authenticated and not request.user.is_staff

    def has_object_permission(self, request, view, obj):
        # The 'obj' here will be a Patient instance.
        # We check if the patient's external_user_id (which links to the auth system)
        # matches the ID of the user making the request.
        return obj.external_user_id == request.user.id

        