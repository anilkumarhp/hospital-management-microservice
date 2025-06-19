# apps/clinical/serializers.py
from rest_framework import serializers
from .models import Patient, Appointment, MedicalRecord, Prescription, PatientDocument, Admission, DailyRound
from apps.operations.models import Branch, User
from apps.operations.serializers import BedSerializer # Reuse the BedSerializer


class PatientSerializer(serializers.ModelSerializer):
    # On GET requests, show the organization's name for readability.
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth',
             'organization_name', 'external_user_id'
        ]
        
        read_only_fields = [
            'external_user_id',
        ]


class AppointmentSerializer(serializers.ModelSerializer):
    # For GET requests, show string representations for readability
    patient = serializers.StringRelatedField(read_only=True)
    doctor = serializers.StringRelatedField(read_only=True)
    branch = serializers.StringRelatedField(read_only=True)

    # For POST requests, we'll expect the IDs for these fields
    patient_id = serializers.UUIDField(write_only=True)
    doctor_id = serializers.IntegerField(write_only=True) # Django User ID is an integer
    branch_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'branch', 'start_time', 'end_time',
            'status', 'notes', 'patient_id', 'doctor_id', 'branch_id'
        ]

    def validate(self, data):
        """
        Check that the patient and branch belong to the user's organization.
        This is our key multi-tenancy validation check.
        """
        request_user = self.context['request'].user
        
        # Superusers can do anything, so we skip validation for them.
        if request_user.is_superuser:
            return data
            
        user_organization = request_user.profile.organization

        # Check the patient
        try:
            patient = Patient.objects.get(id=data['patient_id'])
            if patient.organization != user_organization:
                raise serializers.ValidationError("This patient does not belong to your organization.")
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Invalid patient ID.")

        # Check the branch
        try:
            branch = Branch.objects.get(id=data['branch_id'])
            if branch.organization != user_organization:
                raise serializers.ValidationError("This branch does not belong to your organization.")
        except Branch.DoesNotExist:
            raise serializers.ValidationError("Invalid branch ID.")

        # Check the doctor
        try:
            doctor = User.objects.get(id=data['doctor_id'])
            if doctor.profile.organization != user_organization:
                raise serializers.ValidationError("This doctor does not belong to your organization.")
        except (User.DoesNotExist, User.profile.RelatedObjectDoesNotExist):
            raise serializers.ValidationError("Invalid doctor ID.")

        return data
    
class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        exclude = ('medical_record',) # The record is implied by the URL

class MedicalRecordSerializer(serializers.ModelSerializer):
    # We can nest the prescription serializer to show them all when viewing a record
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        exclude = ('appointment',) # The appointment is implied by the URL

class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDocument
        fields = ['id', 'file', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class PortalDocumentSerializer(serializers.ModelSerializer):
    # This is a special field that calls a method on the serializer
    # to get its value. This is how we generate dynamic data.
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientDocument
        fields = ['id', 'description', 'document_type', 'uploaded_at', 'download_url']

    def get_download_url(self, obj):
        """
        Generates a secure, temporary pre-signed URL for downloading the file from S3.
        The URL will expire after 1 hour (3600 seconds).
        """
        # obj is the PatientDocument instance
        if not obj.file:
            return None
        
        # This calls the underlying S3 storage backend to do the work.
        return obj.file.storage.url(obj.file.name, expire=3600)
    

class DocumentSerializer(serializers.ModelSerializer):
    # Add a field to show the uploader's username
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    # We can also add the uploader's organization name
    uploader_organization = serializers.CharField(source='uploaded_by.profile.organization.name', read_only=True)
    
    # We will also add the secure download URL for the staff member
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientDocument
        fields = [
            'id', 'file', 'description', 'document_type', 'uploaded_at',
            'uploaded_by_username', 'uploader_organization', 'download_url'
        ]
        read_only_fields = ['id', 'uploaded_at']

    def get_download_url(self, obj):
        """Generates a secure, temporary pre-signed URL."""
        if not obj.file:
            return None
        return obj.file.storage.url(obj.file.name, expire=3600)
    

class AdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = ['id', 'patient', 'bed', 'admitted_at', 'status', 'notes']


class ConsolidatedAdmissionSerializer(serializers.ModelSerializer):
    """A detailed serializer for the custom admission summary view."""
    patient = PatientSerializer(read_only=True)
    bed = BedSerializer(read_only=True)
    medical_records = serializers.SerializerMethodField()
    documents = DocumentSerializer(many=True, read_only=True, source='patient.documents')

    class Meta:
        model = Admission
        fields = [
            'id', 'status', 'admitted_at', 'discharged_at', 'notes',
            'patient', 'bed', 'medical_records', 'documents'
        ]

    def get_medical_records(self, obj):
        """
        Custom method to gather all medical records from all appointments
        associated with the admitted patient.
        """
        # obj is the Admission instance
        patient = obj.patient
        # Find all appointments for this patient
        appointments = Appointment.objects.filter(patient=patient)
        # Find all medical records linked to those appointments
        medical_records = MedicalRecord.objects.filter(appointment__in=appointments)
        # Serialize the data
        return MedicalRecordSerializer(medical_records, many=True).data
    
    
class DailyRoundSerializer(serializers.ModelSerializer):
    """Serializer for creating a new daily round/activity log."""
    class Meta:
        model = DailyRound
        # The user provides the service and notes.
        # Admission and staff are set automatically by the view.
        fields = ['id', 'service_provided', 'notes', 'round_time']
        read_only_fields = ['id', 'round_time']