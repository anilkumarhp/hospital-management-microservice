from rest_framework import viewsets, status
from .models import Service, Charge, Invoice
from .serializers import ServiceSerializer, InvoiceSerializer
from apps.operations.permissions import IsOrganizationAdmin
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from datetime import datetime
from django.db import transaction


class ServiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows organization admins to manage their
    catalog of billable services.
    """
    serializer_class = ServiceSerializer
    permission_classes = [IsOrganizationAdmin] # Only Admins can manage services
    tag=["Billing"]

    def get_queryset(self):
        """
        Ensures that admins can only see and manage services
        belonging to their own organization.
        """
        # We don't need a superuser check here, as superusers should
        # not be directly managing organization-specific services.
        # This queryset is inherently secure.
        return Service.objects.filter(organization=self.request.user.profile.organization)

    def perform_create(self, serializer):
        """
        Automatically assigns the new service to the organization of the
        admin creating it.
        """
        serializer.save(organization=self.request.user.profile.organization)


class GenerateInvoiceView(APIView):
    """
    A custom view to generate a partial or full invoice for a patient.
    """
    permission_classes = [IsOrganizationAdmin]

    def post(self, request, *args, **kwargs):
        patient_id = request.data.get('patient_id')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')

        if not all([patient_id, start_date_str, end_date_str]):
            return Response({"error": "patient_id, start_date, and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Find all unbilled charges for this patient in the date range
            charges_to_bill = Charge.objects.filter(
                patient_id=patient_id,
                invoice__isnull=True, # This is the key to prevent double-billing
                billed_at__date__gte=start_date,
                billed_at__date__lte=end_date
            )

            if not charges_to_bill.exists():
                return Response({"message": "No unbilled charges found for this period."}, status=status.HTTP_200_OK)

            # Calculate the total amount
            total_amount = charges_to_bill.aggregate(total=Sum('total_price'))['total'] or 0

            # Create the invoice and link the charges
            with transaction.atomic():
                new_invoice = Invoice.objects.create(
                    patient_id=patient_id,
                    organization=request.user.profile.organization,
                    start_date=start_date,
                    end_date=end_date,
                    total_amount=total_amount
                )
                charges_to_bill.update(invoice=new_invoice)
            
            serializer = InvoiceSerializer(new_invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)