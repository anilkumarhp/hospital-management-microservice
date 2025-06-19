# apps/clinical/portal_serializers.py
from rest_framework import serializers
from .models import Appointment, MedicalRecord, Prescription, PatientDocument

class PortalPrescriptionSerializer(serializers.ModelSerializer):
    """
    A simple serializer for prescriptions, showing only patient-relevant info.
    """
    class Meta:
        model = Prescription
        fields = ['medication', 'dosage', 'frequency', 'duration_days']


class PortalMedicalRecordSerializer(serializers.ModelSerializer):
    """
    A serializer for medical records that exposes only patient-safe fields.
    It also includes all related prescriptions.
    """
    # We nest the prescription serializer to show them all when viewing a record
    prescriptions = PortalPrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        fields = ['id', 'diagnosis', 'prescriptions'] # Note: we are excluding 'notes'


class PortalAppointmentSerializer(serializers.ModelSerializer):
    """
    A patient-facing serializer for appointments that includes the nested medical record.
    """
    # This will show the full medical record (using its serializer) if it exists.
    medical_record = PortalMedicalRecordSerializer(read_only=True)
    doctor = serializers.StringRelatedField(read_only=True)
    branch = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'doctor', 'branch', 'start_time', 'end_time', 'status', 'medical_record']


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