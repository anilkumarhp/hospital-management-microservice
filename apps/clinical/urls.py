from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    PatientViewSet, AppointmentViewSet, MedicalRecordViewSet,
    PrescriptionViewSet, PatientDocumentViewSet, AdmissionViewSet,
    ConsolidatedAdmissionDetailView, PatientReportSummaryView, LogAdmissionActivityView,
)

# --- Main Router ---
router = routers.DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')
router.register(r'admissions', AdmissionViewSet, basename='admission')

# --- Nested Routers ---
patients_router = routers.NestedDefaultRouter(router, r'patients', lookup='patient')
patients_router.register(r'documents', PatientDocumentViewSet, basename='patient-documents')

appointments_router = routers.NestedDefaultRouter(router, r'appointments', lookup='appointment')
appointments_router.register(r'medical-record', MedicalRecordViewSet, basename='appointment-medical-record')

medical_records_router = routers.NestedDefaultRouter(router, r'medical-records', lookup='medical_record')
medical_records_router.register(r'prescriptions', PrescriptionViewSet, basename='medical-record-prescriptions')


# --- Combine All URL Patterns ---
urlpatterns = [
    # Include all router-generated URLs first.
    # This automatically includes standard URLs AND custom action URLs.
    path('', include(router.urls)),
    path('', include(patients_router.urls)),
    path('', include(appointments_router.urls)),
    path('', include(medical_records_router.urls)),
    
     path(
        'admissions/<uuid:admission_id>/log-activity/',
        LogAdmissionActivityView.as_view(),
        name='admission-log-activity'
    ),
    # Manually add paths for custom APIViews that DO NOT use a router.
    path(
        'patients/<uuid:patient_pk>/report-summary/',
        PatientReportSummaryView.as_view(),
        name='patient-report-summary'
    ),
    path(
        'admissions/<uuid:admission_id>/details/',
        ConsolidatedAdmissionDetailView.as_view(),
        name='admission-detail-summary'
    ),
]