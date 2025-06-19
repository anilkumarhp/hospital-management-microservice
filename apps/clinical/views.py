# apps/clinical/views.py
from rest_framework import viewsets, permissions, status, serializers
from .models import Patient, Admission, Appointment, MedicalRecord, Prescription, PatientDocument, DailyRound
from .serializers import PatientSerializer, AppointmentSerializer,  AppointmentSerializer, MedicalRecordSerializer, PrescriptionSerializer, DocumentUploadSerializer, DocumentSerializer, DailyRoundSerializer, ConsolidatedAdmissionSerializer, AdmissionSerializer
from apps.operations.permissions import CanManagePatients
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.billing.models import Service, Charge
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view
from apps.operations.models import Bed
from django.db import transaction

class AdmissionViewSet(viewsets.ModelViewSet):
    """API for staff to manage patient admissions."""
    # The @action for 'log_activity' has been REMOVED from this ViewSet.
    serializer_class = AdmissionSerializer
    permission_classes = [CanManagePatients]
    tags = ['[Clinical Staff] - Admissions']

    def get_queryset(self):
        return Admission.objects.filter(patient__organization=self.request.user.profile.organization)

    def perform_create(self, serializer):
        bed = serializer.validated_data['bed']
        if bed.status != Bed.BedStatus.AVAILABLE:
            raise serializers.ValidationError("This bed is not available.")
        
        with transaction.atomic():
            bed.status = Bed.BedStatus.OCCUPIED
            bed.save()
            serializer.save()


class LogAdmissionActivityView(APIView):
    """
    A dedicated endpoint to log a new activity (like a doctor's visit)
    for a specific admission.
    """
    permission_classes = [CanManagePatients]
    serializer_class = DailyRoundSerializer # For Swagger documentation

    def post(self, request, admission_id=None):
        """
        Creates a DailyRound record and its associated Charge.
        """
        try:
            # Ensure the admission exists and belongs to the user's organization
            admission = Admission.objects.get(
                id=admission_id, 
                patient__organization=request.user.profile.organization
            )
        except Admission.DoesNotExist:
            return Response({"error": "Admission not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DailyRoundSerializer(data=request.data)
        if serializer.is_valid():
            service = serializer.validated_data.get('service_provided')
            
            with transaction.atomic():
                new_charge = Charge.objects.create(
                    patient=admission.patient,
                    service=service,
                    quantity=1
                )
                serializer.save(
                    admission=admission,
                    performed_by=request.user,
                    charge=new_charge
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@extend_schema(tags=["Patient"])
class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [CanManagePatients]
    TAGS = ['Patient']

    def get_queryset(self):
        """
        ★-- REAL SECURITY LOGIC --★
        Filter patients based on the organization of the logged-in user's profile.
        """
        user = self.request.user
        if user.is_superuser:
            return Patient.objects.all()
        
        # Using select_related('profile') is a performance optimization.
        # It fetches the user and their profile in a single database query.
        return Patient.objects.filter(organization=user.profile.organization)

    def perform_create(self, serializer):
        """
        ★-- REAL DATA INTEGRITY --★
        Automatically assign the new patient to the organization of the user
        who is creating them.
        """
        serializer.save(organization=self.request.user.profile.organization)


@extend_schema(tags=["Appointment"])
class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [CanManagePatients]
    tags = ['Clinical Staff - Appointments']

    def get_queryset(self):
        """Users can only see appointments within their own organization."""
        user = self.request.user
        if user.is_superuser:
            return Appointment.objects.all()

        # Using `select_related` is a performance boost!
        return Appointment.objects.select_related(
            'patient', 'doctor', 'branch'
        ).filter(branch__organization=user.profile.organization)

    def perform_create(self, serializer):
        """On create, we don't need to inject the organization as it's
           linked via the Branch, which is already validated."""
        serializer.save()

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_appointment(self, request, pk=None):
        """
        A custom action to mark an appointment as 'COMPLETED' and
        automatically generate the corresponding charge for the consultation.
        """
        # Get the specific appointment instance
        appointment = self.get_object()

        # 1. Check if the appointment can be completed
        if appointment.status == Appointment.AppointmentStatus.COMPLETED:
            return Response(
                {"error": "This appointment has already been completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Find the default "Consultation" service for this organization
        try:
            consultation_service = Service.objects.get(
                organization=appointment.branch.organization,
                category=Service.ServiceCategory.CONSULTATION
            )
        except Service.DoesNotExist:
            return Response(
                {"error": "A default 'Consultation' service has not been configured for this organization."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Service.MultipleObjectsReturned:
             return Response(
                {"error": "Multiple 'Consultation' services found. Please configure only one default."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Update the appointment status
        appointment.status = Appointment.AppointmentStatus.COMPLETED
        appointment.save()

        # 4. Create the charge for the patient
        # ★-- THE FIX --★
        # We now explicitly pass the price and quantity to avoid the TypeError.
        # The model's save() method will still calculate the total_price.
        Charge.objects.create(
            patient=appointment.patient,
            service=consultation_service,
            quantity=1,
            price_at_charge=consultation_service.price
        )
        
        # 5. Return a success response
        # We can return the updated appointment data
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)


@extend_schema(tags=["Medical Records"])
class MedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalRecordSerializer
    permission_classes = [CanManagePatients]
    tags = ['[Medical Records']

    def get_queryset(self):
        # This queryset is filtered by the appointment_pk from the nested URL
        return MedicalRecord.objects.filter(appointment_id=self.kwargs['appointment_pk'])

    def perform_create(self, serializer):
        # Automatically associate the record with the appointment from the URL
        appointment = Appointment.objects.get(id=self.kwargs['appointment_pk'])
        serializer.save(appointment=appointment)

@extend_schema(tags=["Prescriptions"])
class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [CanManagePatients]
    tags = ['[Staff] Prescription']


    def get_queryset(self):
        return Prescription.objects.filter(medical_record_id=self.kwargs['medical_record_pk'])

    def perform_create(self, serializer):
        medical_record = MedicalRecord.objects.get(id=self.kwargs['medical_record_pk'])
        serializer.save(medical_record=medical_record)

@extend_schema(tags=["Patient Documents"])
class PatientDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentUploadSerializer
    permission_classes = [CanManagePatients]
    # We need to add file upload parsers
    parser_classes = [MultiPartParser, FormParser]
    tags = ['[Staff] Patient']

    def get_queryset(self):
        # Filter documents by the patient_pk from the nested URL
        return PatientDocument.objects.filter(patient_id=self.kwargs['patient_pk'])

    def perform_create(self, serializer):
        patient = Patient.objects.get(id=self.kwargs['patient_pk'])
        # Associate the document with the patient from the URL and the user uploading
        serializer.save(patient=patient, uploaded_by=self.request.user)


class PatientReportSummaryView(APIView):
    """
    A custom view to get a summary of a patient's documents,
    grouped by internal and external organizations.
    """
    permission_classes = [CanManagePatients] # Only authorized staff can access
    tags = ['[Staff] patient report']

    def get(self, request, patient_pk=None):
        # First, ensure the requested patient exists and belongs to the user's org
        try:
            patient = Patient.objects.get(id=patient_pk, organization=request.user.profile.organization)
        except Patient.DoesNotExist:
            return Response(
                {"status": "error", "error": {"code": 404, "message": "Patient not found in your organization."}},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch all documents for this patient, ordered by date
        documents = PatientDocument.objects.filter(patient=patient).select_related(
            'uploaded_by__profile__organization'
        ).order_by('-uploaded_at')

        # Prepare the data structures for our response
        internal_reports = []
        external_reports = {}

        # Loop through the documents and group them
        for doc in documents:
            # Check if the uploader has a profile and organization
            if hasattr(doc.uploaded_by, 'profile') and doc.uploaded_by.profile.organization:
                uploader_org = doc.uploaded_by.profile.organization
                
                if uploader_org == patient.organization:
                    internal_reports.append(doc)
                else:
                    # Group external reports by the uploader's organization name
                    org_name = uploader_org.name
                    if org_name not in external_reports:
                        external_reports[org_name] = []
                    external_reports[org_name].append(doc)

        # Serialize the grouped data
        internal_serializer = DocumentSerializer(internal_reports, many=True)
        external_serialized = {}
        for org_name, docs_list in external_reports.items():
            external_serialized[org_name] = DocumentSerializer(docs_list, many=True).data

        # Construct the final response payload
        response_data = {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "internal_reports": internal_serializer.data,
            "external_reports": external_serialized
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

class AdmissionViewSet(viewsets.ModelViewSet):
    """API for staff to manage patient admissions."""
    serializer_class = AdmissionSerializer
    permission_classes = [CanManagePatients]

    def get_queryset(self):
        # ... queryset logic to filter by user's organization ...
        return Admission.objects.filter(patient__organization=self.request.user.profile.organization)

    def perform_create(self, serializer):
        # When creating an admission, mark the chosen bed as OCCUPIED
        bed = serializer.validated_data['bed']
        if bed.status != 'AVAILABLE':
            raise serializers.ValidationError("This bed is not available.")
        bed.status = 'OCCUPIED'
        bed.save()
        serializer.save()

class ConsolidatedAdmissionDetailView(APIView):
    """Provides a complete, detailed summary for a single admission."""
    permission_classes = [CanManagePatients]

    def get(self, request, admission_id=None):
        try:
            # Fetch the core admission object, ensuring it's in the user's org
            admission = Admission.objects.select_related(
                'patient', 'bed__branch'
            ).get(
                id=admission_id, 
                patient__organization=request.user.profile.organization
            )
            serializer = ConsolidatedAdmissionSerializer(admission)
            return Response(serializer.data)
        except Admission.DoesNotExist:
            return Response({"error": "Admission not found."}, status=status.HTTP_404_NOT_FOUND)
        


