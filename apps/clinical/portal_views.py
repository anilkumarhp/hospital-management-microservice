# apps/clinical/portal_views.py
from rest_framework import viewsets, permissions
from .models import Patient, Appointment
from .serializers import PatientSerializer, AppointmentSerializer, PatientDocument
from .portal_serializers import PortalAppointmentSerializer, PortalDocumentSerializer 

class MyProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only endpoint for the logged-in patient to view their own profile.
    """
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated] # Basic login check first
    tags = ['[Portal] Profile']

    def get_queryset(self):
        """
        This view should only ever return the patient record for the logged-in user.
        """
        # We find the patient record whose external_user_id matches the
        # ID of the user from the JWT token.
        return Patient.objects.filter(external_user_id=self.request.user.id)
    

class MyAppointmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only endpoint for the logged-in patient to view their own appointments.
    """
    serializer_class = PortalAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    tags = ['[Staff] Appointment']
    
    def get_queryset(self):
        """
        This is the key security feature. It filters the appointments to an
        absolute list of only those belonging to the logged-in user.
        """
        # We use select_related for a performance boost, fetching all related
        # data in a single, efficient database query.
        return Appointment.objects.select_related(
            'patient', 'doctor', 'branch'
        ).filter(patient__external_user_id=self.request.user.id)


class MyDocumentsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only endpoint for a patient to list all their documents
    and get secure download links.
    """
    serializer_class = PortalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    tags = ['[Staff] Documents']

    def get_queryset(self):
        """
        This view only ever returns documents for the logged-in user.
        """
        return PatientDocument.objects.filter(patient__external_user_id=self.request.user.id)