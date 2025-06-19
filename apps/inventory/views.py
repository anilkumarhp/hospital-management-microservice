from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Medication, MedicationStock
from .serializers import MedicationSerializer, MedicationStockSerializer
from apps.operations.permissions import IsOrganizationAdmin
from apps.operations.permissions import CanManagePatients


class MedicationViewSet(viewsets.ModelViewSet):
    """API for Admins to manage the organization's Medication catalog."""
    serializer_class = MedicationSerializer
    permission_classes = [IsOrganizationAdmin]

    def get_queryset(self):
        """Admins can only see medications from their own organization."""
        return Medication.objects.filter(organization=self.request.user.profile.organization)

    def perform_create(self, serializer):
        """Automatically assign the medication to the admin's organization."""
        serializer.save(organization=self.request.user.profile.organization)


class MedicationStockViewSet(viewsets.ModelViewSet):
    """API for Admins to manage medication stock levels."""
    serializer_class = MedicationStockSerializer
    permission_classes = [IsOrganizationAdmin]

    def get_queryset(self):
        """Admins can only see stock from branches in their own organization."""
        return MedicationStock.objects.filter(branch__organization=self.request.user.profile.organization)
        
    # We don't need a perform_create here because the serializer's validate
    # method already ensures the branch and medication belong to the user's org.

class StockCheckView(APIView):
    """
    A custom, read-only view for doctors to check the availability of a
    medication at a specific branch in real-time.
    """
    # Any authenticated staff member (Doctor, Admin, etc.) can check stock.
    permission_classes = [CanManagePatients]

    def get(self, request, *args, **kwargs):
        # 1. Get query parameters from the URL
        branch_id = request.query_params.get('branch_id', None)
        medication_name = request.query_params.get('medication_name', None)

        # 2. Validate input
        if not branch_id or not medication_name:
            return Response(
                {"error": "Both 'branch_id' and 'medication_name' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Perform the database lookup
        try:
            # We look for a stock record that matches the branch and where the medication
            # name contains the search term (case-insensitive).
            stock = MedicationStock.objects.get(
                branch_id=branch_id,
                medication__name__icontains=medication_name,
                # Security check: Ensure the branch belongs to the user's organization
                branch__organization=request.user.profile.organization
            )
            
            # 4. Construct the success response
            response_data = {
                "status": "In Stock",
                "medication_id": stock.medication.id,
                "medication_name": stock.medication.name,
                "branch_id": stock.branch.id,
                "branch_name": stock.branch.name,
                "quantity": stock.quantity
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except MedicationStock.DoesNotExist:
            # 4. Construct the "not found" response
            return Response(
                {"status": "Out of Stock or Medication Not Found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except MedicationStock.MultipleObjectsReturned:
            # Handle cases where multiple medications match the search term
            return Response(
                {"status": "Multiple Matches", "error": "Search term is not specific enough."},
                status=status.HTTP_400_BAD_REQUEST
            )