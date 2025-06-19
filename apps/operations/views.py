from rest_framework import viewsets,  permissions, mixins
from .models import Organization, Branch, UserInvite, StaffAvailability, LeaveRequest, UserProfile, Bed
from .serializers import OrganizationSerializer, BranchSerializer, UserInviteSerializer, StaffAvailabilitySerializer, LeaveRequestSerializer, BedSerializer
from .permissions import IsAdminForOwnOrganization, IsOrganizationAdmin
from datetime import datetime, timedelta
from .tasks import publish_user_invited_event, process_conflicts_for_single_leave
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    A simple ViewSet for viewing organizations.
    """
    # queryset: Defines the collection of objects that are available for the view.
    queryset = Organization.objects.all()
    # serializer_class: Specifies the serializer to use for this view.
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminForOwnOrganization]
    tags = ['Organization']


class BranchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing branches.
    Crucially, the queryset is filtered based on the user's organization.
    """
    serializer_class = BranchSerializer
    permission_classes = [IsOrganizationAdmin] # Use the standard IsAuthenticated for now
    tags = ['Branches']

    def get_queryset(self):
        """
        ★-- APPLYING MULTI-TENANCY --★
        This method overrides the default queryset to ensure that users can only
        see branches belonging to their own organization.
        """
        user = self.request.user
        if user.is_superuser:
            return Branch.objects.all()
        
        # For a regular user, filter by their profile's organization.
        # This prevents any data leakage between tenants.
        return Branch.objects.filter(organization=user.profile.organization)

    def perform_create(self, serializer):
        """
        ★-- THE FIX --★
        When a new branch is created, we ALWAYS assign it to the
        organization of the user creating it. A superuser is the only
        exception and must provide the org ID in the payload.
        """
        if self.request.user.is_superuser:
            # This path is now ONLY for the superuser in the browsable API
            # where they can select an organization from a dropdown.
            serializer.save()
        else:
            # For ANY regular authenticated user (Admin, Doctor, etc.),
            # we enforce their own organization.
            serializer.save(organization=self.request.user.profile.organization)


class UserInviteViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for creating and listing user invitations.
    - POST: Creates a new invitation for the admin's organization.
    - GET: Lists pending invitations for the admin's organization.
    """
    # This line is essential for both GET (list) and POST (create) actions.
    serializer_class = UserInviteSerializer
    
    permission_classes = [IsOrganizationAdmin]
    tags = ['Invites']

    def get_queryset(self):
        """
        This method is required by ListModelMixin for GET requests.
        Admins should only be able to see invites for their own organization.
        """
        user = self.request.user
        if user.is_superuser:
            return UserInvite.objects.all()
        
        return UserInvite.objects.filter(organization=user.profile.organization)

    def perform_create(self, serializer):
        """
        This method is required by CreateModelMixin for POST requests.
        Set the organization from the inviting admin's profile.
        """
        serializer.save(
            organization=self.request.user.profile.organization,
            expires_at=datetime.now() + timedelta(days=7)
        )

class StaffAvailabilityViewSet(viewsets.ModelViewSet):
    """API for Admins to manage the weekly availability of staff."""
    serializer_class = StaffAvailabilitySerializer
    permission_classes = [IsOrganizationAdmin]

    def get_queryset(self):
        """Admins can only see availability for staff in their own organization."""
        return StaffAvailability.objects.filter(
            staff_profile__organization=self.request.user.profile.organization
        )

class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    API for staff to request leave and for Admins to approve/reject it.
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    tags = ['[Operations] - Leave Requests']

    def get_queryset(self):
        """
        Admins see all leave requests for their organization.
        Regular staff only see their own leave requests.
        """
        user = self.request.user
        # This check is important to avoid errors if a user has no profile
        if not hasattr(user, 'profile'):
             return LeaveRequest.objects.none()

        if user.profile.role == UserProfile.Roles.ADMIN:
            return LeaveRequest.objects.filter(staff_profile__organization=user.profile.organization)
        
        return LeaveRequest.objects.filter(staff_profile=user.profile)

    def perform_create(self, serializer):
        """Automatically assign the leave request to the user creating it."""
        serializer.save(staff_profile=self.request.user.profile)

    @action(detail=True, methods=['post'], permission_classes=[IsOrganizationAdmin])
    def review(self, request, pk=None):
        """
        A custom action for an ADMIN to approve or reject a leave request.
        """
        leave_request = self.get_object()
        
        new_status = request.data.get('status')
        if new_status not in [LeaveRequest.LeaveStatus.APPROVED, LeaveRequest.LeaveStatus.REJECTED]:
            return Response(
                {'error': "Invalid status. Must be 'APPROVED' or 'REJECTED'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request.status = new_status
        leave_request.reviewed_by = request.user
        leave_request.reviewed_at = datetime.now()
        leave_request.save()
        
        if leave_request.status == LeaveRequest.LeaveStatus.APPROVED:
            process_conflicts_for_single_leave.delay(str(leave_request.id))

        return Response(self.get_serializer(leave_request).data)
    
class BedViewSet(viewsets.ReadOnlyModelViewSet):
    """A read-only endpoint for admins to view and filter beds."""
    serializer_class = BedSerializer
    permission_classes = [IsOrganizationAdmin]
    # ★-- UPDATED FILTERS --★
    filterset_fields = ['branch', 'category', 'status', 'building', 'floor_number']

    def get_queryset(self):
        return Bed.objects.filter(branch__organization=self.request.user.profile.organization)
    

