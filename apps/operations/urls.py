from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, BranchViewSet, UserInviteViewSet, StaffAvailabilityViewSet, LeaveRequestViewSet, BedViewSet


# DRF's routers automatically generate the URL patterns for a ViewSet.
# e.g., /organizations/ and /organizations/{id}/
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'invites', UserInviteViewSet, basename='invite')
router.register(r'staff-availability', StaffAvailabilityViewSet, basename='staff-availability')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'beds', BedViewSet, basename='bed')


urlpatterns = router.urls