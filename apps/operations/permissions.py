# apps/operations/permissions.py
from rest_framework import permissions
from .models import UserProfile

class IsAdminForOwnOrganization(permissions.BasePermission):
    """
    Custom permission to only allow admins of an organization to see it.
    This enforces tenant isolation.
    """
    
    def has_permission(self, request, view):
        """
        ★-- THIS IS THE FIX --★
        This is the "front door" check. It runs on all requests.
        We simply check if the user is authenticated at all.
        If they aren't logged in, they can't go any further.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # The 'obj' here is an Organization instance.
        # We need to check if the logged-in user (request.user) belongs to
        # this organization and has an admin role.

        # For now, we'll make a simplifying assumption that the superuser
        # can see everything. We'll build out the real logic later.
        if request.user.is_superuser:
            return True
        
        # ★-- The REAL logic will go here. It will look something like:
        # return request.user.organization == obj and request.user.has_role('ADMIN')
        
        # For now, let's keep it simple for testing.
        return False
    
class IsOrganizationAdmin(permissions.BasePermission):
    """Permission to only allow users with the 'ADMIN' role."""
    def has_permission(self, request, view):
        # ★-- THE FIX --★
        # This now correctly checks if the user is logged in, has a profile,
        # and if that profile's role is ADMIN.
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role == UserProfile.Roles.ADMIN
        )

class CanManagePatients(permissions.BasePermission):
    """Permission to allow users who are DOCTORs or ADMINs."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role in [UserProfile.Roles.ADMIN, UserProfile.Roles.DOCTOR]
        )