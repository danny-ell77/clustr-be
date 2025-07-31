"""
Views for utility bill automation features.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from core.common.models import (
    UtilityProvider,
    Bill,
    RecurringPayment,
    Wallet,
    BillCategory,
    RecurringPaymentStatus,
)
from core.common.serializers.utility_serializers import (
    UtilityProviderSerializer,
    UtilityBillSerializer,
    RecurringUtilityPaymentSerializer,
    UtilityCustomerValidationSerializer,
    UtilityPaymentSerializer,
    SetupRecurringUtilityPaymentSerializer,
)
from core.common.services.utility_service import UtilityPaymentManager

logger = logging.getLogger("clustr")


class UtilityProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for utility providers."""

    serializer_class = UtilityProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get utility providers for user's cluster."""
        return UtilityProvider.objects.filter(
            cluster=self.request.user.cluster,
            is_active=True
        ).order_by("name")

    @action(detail=False, methods=["get"])
    def by_type(self, request):
        """Get utility providers grouped by type."""
        providers = self.get_queryset()
        grouped = {}
        
        for provider in providers:
            provider_type = provider.provider_type
            if provider_type not in grouped:
                grouped[provider_type] = []
            grouped[provider_type].append(self.get_serializer(provider).data)
        
        return Response(grouped)


class UtilityBillViewSet(viewsets.ModelViewSet):
    """ViewSet for utility bills."""

    serializer_class = UtilityBillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get utility bills for the current user."""
        return Bill.objects.filter(
            user_id=self.request.user.id,
            cluster=self.request.user.cluster,
            category=BillCategory.USER_MANAGED
        ).select_related("utility_provider").order_by("-created_at")

    def perform_create(self, serializer):
        """Create utility bill with user context."""
        serializer.save(
            user_id=self.request.user.id,
            cluster=self.request.user.cluster,
            category=BillCategory.USER_MANAGED,
            created_by_user=True,
            created_by=self.request.user.id,
            last_modified_by=self.request.user.id,
        )

    def perform_update(self, serializer):
        """Update utility bill with user context."""
        serializer.save(last_modified_by=self.request.user.id)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get utility bills summary."""
        bills = self.get_queryset()
        
        summary = {
            "total_bills": bills.count(),
            "paid_bills": bills.filter(status="paid").count(),
            "pending_bills": bills.filter(status__in=["pending", "acknowledged"]).count(),
            "overdue_bills": bills.filter(due_date__lt=timezone.now()).exclude(status="paid").count(),
            "total_amount": sum(bill.amount for bill in bills),
            "paid_amount": sum(bill.paid_amount for bill in bills),
        }
        
        return Response(summary)


class RecurringUtilityPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for recurring utility payments."""

    serializer_class = RecurringUtilityPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get recurring utility payments for the current user."""
        return RecurringPayment.objects.filter(
            user_id=self.request.user.id,
            cluster=self.request.user.cluster,
            utility_provider__isnull=False
        ).select_related("utility_provider", "wallet").order_by("-created_at")

    def perform_create(self, serializer):
        """Create recurring payment with user context."""
        # Get user's wallet
        try:
            wallet = Wallet.objects.get(
                user_id=self.request.user.id,
                cluster=self.request.user.cluster
            )
        except Wallet.DoesNotExist:
            return Response(
                {"error": "User wallet not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save(
            user_id=self.request.user.id,
            cluster=self.request.user.cluster,
            wallet=wallet,
            created_by=self.request.user.id,
            last_modified_by=self.request.user.id,
        )

    def perform_update(self, serializer):
        """Update recurring payment with user context."""
        serializer.save(last_modified_by=self.request.user.id)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause recurring payment."""
        recurring_payment = self.get_object()
        
        if recurring_payment.status != RecurringPaymentStatus.ACTIVE:
            return Response(
                {"error": "Only active payments can be paused"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recurring_payment.pause()
        return Response({"message": "Recurring payment paused successfully"})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """Resume recurring payment."""
        recurring_payment = self.get_object()
        
        if recurring_payment.status != RecurringPaymentStatus.PAUSED:
            return Response(
                {"error": "Only paused payments can be resumed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recurring_payment.resume()
        return Response({"message": "Recurring payment resumed successfully"})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel recurring payment."""
        recurring_payment = self.get_object()
        
        if recurring_payment.status == RecurringPaymentStatus.CANCELLED:
            return Response(
                {"error": "Payment is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recurring_payment.cancel()
        return Response({"message": "Recurring payment cancelled successfully"})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get recurring payments summary."""
        payments = self.get_queryset()
        
        summary = {
            "total_payments": payments.count(),
            "active_payments": payments.filter(status=RecurringPaymentStatus.ACTIVE).count(),
            "paused_payments": payments.filter(status=RecurringPaymentStatus.PAUSED).count(),
            "cancelled_payments": payments.filter(status=RecurringPaymentStatus.CANCELLED).count(),
            "total_monthly_amount": sum(
                payment.amount for payment in payments.filter(
                    status=RecurringPaymentStatus.ACTIVE,
                    frequency="monthly"
                )
            ),
            "next_payments": payments.filter(
                status=RecurringPaymentStatus.ACTIVE,
                next_payment_date__gte=timezone.now()
            ).order_by("next_payment_date")[:5].values(
                "id", "title", "amount", "next_payment_date"
            ),
        }
        
        return Response(summary)


class UtilityPaymentViewSet(viewsets.ViewSet):
    """ViewSet for utility payment operations."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def validate_customer(self, request):
        """Validate utility customer."""
        serializer = UtilityCustomerValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            utility_provider = UtilityProvider.objects.get(
                id=serializer.validated_data["utility_provider_id"],
                cluster=request.user.cluster
            )
        except UtilityProvider.DoesNotExist:
            return Response(
                {"error": "Utility provider not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        result = UtilityPaymentManager.validate_utility_customer(
            utility_provider=utility_provider,
            customer_id=serializer.validated_data["customer_id"]
        )

        if result.get("success"):
            return Response(result)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def pay_utility(self, request):
        """Process one-time utility payment."""
        serializer = UtilityPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            utility_provider = UtilityProvider.objects.get(
                id=serializer.validated_data["utility_provider_id"],
                cluster=request.user.cluster
            )
        except UtilityProvider.DoesNotExist:
            return Response(
                {"error": "Utility provider not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            wallet = Wallet.objects.get(
                user_id=request.user.id,
                cluster=request.user.cluster
            )
        except Wallet.DoesNotExist:
            return Response(
                {"error": "User wallet not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = UtilityPaymentManager.process_utility_payment(
            user_id=request.user.id,
            utility_provider=utility_provider,
            customer_id=serializer.validated_data["customer_id"],
            amount=serializer.validated_data["amount"],
            wallet=wallet,
            description=serializer.validated_data.get("description")
        )

        if result.get("success"):
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def setup_recurring(self, request):
        """Set up recurring utility payment."""
        serializer = SetupRecurringUtilityPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            utility_provider = UtilityProvider.objects.get(
                id=serializer.validated_data["utility_provider_id"],
                cluster=request.user.cluster
            )
        except UtilityProvider.DoesNotExist:
            return Response(
                {"error": "Utility provider not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            wallet = Wallet.objects.get(
                user_id=request.user.id,
                cluster=request.user.cluster
            )
        except Wallet.DoesNotExist:
            return Response(
                {"error": "User wallet not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = UtilityPaymentManager.setup_recurring_utility_payment(
            user_id=request.user.id,
            utility_provider=utility_provider,
            customer_id=serializer.validated_data["customer_id"],
            amount=serializer.validated_data["amount"],
            frequency=serializer.validated_data["frequency"],
            wallet=wallet,
            title=serializer.validated_data.get("title"),
            description=serializer.validated_data.get("description"),
            payment_source=serializer.validated_data.get("payment_source", "wallet"),
            spending_limit=serializer.validated_data.get("spending_limit"),
            start_date=serializer.validated_data.get("start_date", timezone.now()),
            next_payment_date=serializer.validated_data.get("start_date", timezone.now()),
        )

        if result.get("success"):
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def payment_history(self, request):
        """Get user's utility payment history."""
        bills = UtilityPaymentManager.get_user_utility_bills(
            user_id=request.user.id,
            cluster=request.user.cluster
        )

        # Filter by query parameters
        bill_type = request.query_params.get("type")
        if bill_type:
            bills = bills.filter(type=bill_type)

        bill_status = request.query_params.get("status")
        if bill_status:
            bills = bills.filter(status=bill_status)

        # Paginate results
        from django.core.paginator import Paginator
        paginator = Paginator(bills, 20)
        page_number = request.query_params.get("page", 1)
        page_obj = paginator.get_page(page_number)

        serializer = UtilityBillSerializer(page_obj.object_list, many=True)
        
        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        })