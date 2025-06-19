# apps/clinical/portal_urls.py
from rest_framework.routers import DefaultRouter
from .portal_views import MyProfileViewSet, MyAppointmentViewSet, MyDocumentsViewSet

router = DefaultRouter()
router.register(r'my-profile', MyProfileViewSet, basename='my-profile')
router.register(r'my-appointments', MyAppointmentViewSet, basename='my-appointment')
router.register(r'my-documents', MyDocumentsViewSet, basename='my-document')

urlpatterns = router.urls