"""
Serializers for utility bill automation features.
"""

from rest_framework import serializers
from decimal import Decimal

from core.common.models import (
    UtilityProvider,
    Bill,
    RecurringPayment,
    BillCategory,
    RecurringPaymentFrequency,
    RecurringPaymentStatus,
)


class UtilityProviderSerializer(serializers.ModelSerializer):
    """Serializer for UtilityProvider model."""

    class Meta:
        model = UtilityProvider
        fields = [
            "id",
            "name",
            "provider_type",
            "api_provider",
            "provider_code",
            "is_active",
            "supports_validation",
            "supports_info_lookup",
            "minimum_amount",
            "maximum_amount",
            "metadata",
            "created_at",
            "last_modified_at",
        ]
        read_only_fields = ["id", "created_at", "last_modified_at"]


class UtilityBillSerializer(serializers.ModelSerializer):
    """Serializer for utility bills."""

    utility_provider_name = serializers.CharField(
        source="utility_provider.name", read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "title",
            "description",
            "type",
            "category",
            "amount",
            "currency",
            "utility_provider",
            "utility_provider_name",
            "customer_id",
            "is_automated",
            "due_date",
            "paid_amount",
            "remaining_amount",
            "paid_at",
            "is_overdue",
            "metadata",
            "created_at",
            "last_modified_at",
        ]
        read_only_fields = [
            "id",
            "bill_number",
            "paid_amount",
            "paid_at",
            "remaining_amount",
            "is_overdue",
            "created_at",
            "last_modified_at",
        ]

    def validate(self, data):
        """Validate utility bill data."""
        if data.get("category") == BillCategory.USER_MANAGED:
            if not data.get("utility_provider"):
                raise serializers.ValidationError(
                    "Utility provider is required for user-managed bills"
                )
            if not data.get("customer_id"):
                raise serializers.ValidationError(
                    "Customer ID is required for utility bills"
                )
        return data


class RecurringUtilityPaymentSerializer(serializers.ModelSerializer):
    """Serializer for recurring utility payments."""

    utility_provider_name = serializers.CharField(
        source="utility_provider.name", read_only=True
    )
    next_payment_in_days = serializers.SerializerMethodField()
    can_be_paused = serializers.SerializerMethodField()
    can_be_resumed = serializers.SerializerMethodField()

    class Meta:
        model = RecurringPayment
        fields = [
            "id",
            "title",
            "description",
            "amount",
            "currency",
            "frequency",
            "status",
            "utility_provider",
            "utility_provider_name",
            "customer_id",
            "payment_source",
            "spending_limit",
            "start_date",
            "end_date",
            "next_payment_date",
            "last_payment_date",
            "total_payments",
            "failed_attempts",
            "max_failed_attempts",
            "next_payment_in_days",
            "can_be_paused",
            "can_be_resumed",
            "metadata",
            "created_at",
            "last_modified_at",
        ]
        read_only_fields = [
            "id",
            "last_payment_date",
            "total_payments",
            "failed_attempts",
            "next_payment_in_days",
            "can_be_paused",
            "can_be_resumed",
            "created_at",
            "last_modified_at",
        ]

    def get_next_payment_in_days(self, obj):
        """Calculate days until next payment."""
        if obj.next_payment_date:
            from django.utils import timezone

            delta = obj.next_payment_date - timezone.now()
            return max(0, delta.days)
        return None

    def get_can_be_paused(self, obj):
        """Check if payment can be paused."""
        return obj.status == RecurringPaymentStatus.ACTIVE

    def get_can_be_resumed(self, obj):
        """Check if payment can be resumed."""
        return obj.status == RecurringPaymentStatus.PAUSED

    def validate(self, data):
        """Validate recurring payment data."""
        if data.get("utility_provider") and not data.get("customer_id"):
            raise serializers.ValidationError(
                "Customer ID is required for utility payments"
            )

        if data.get("spending_limit") and data.get("amount"):
            if data["spending_limit"] < data["amount"]:
                raise serializers.ValidationError(
                    "Spending limit cannot be less than payment amount"
                )

        return data


class UtilityCustomerValidationSerializer(serializers.Serializer):
    """Serializer for utility customer validation."""

    utility_provider_id = serializers.UUIDField()
    customer_id = serializers.CharField(max_length=100)

    def validate_utility_provider_id(self, value):
        """Validate utility provider exists."""
        try:
            UtilityProvider.objects.get(id=value)
        except UtilityProvider.DoesNotExist:
            raise serializers.ValidationError("Utility provider not found")
        return value


class UtilityPaymentSerializer(serializers.Serializer):
    """Serializer for one-time utility payments."""

    utility_provider_id = serializers.UUIDField()
    customer_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(max_length=500, required=False)

    def validate_utility_provider_id(self, value):
        """Validate utility provider exists and is active."""
        try:
            provider = UtilityProvider.objects.get(id=value)
            if not provider.is_active:
                raise serializers.ValidationError("Utility provider is not active")
        except UtilityProvider.DoesNotExist:
            raise serializers.ValidationError("Utility provider not found")
        return value

    def validate(self, data):
        """Validate payment data."""
        try:
            provider = UtilityProvider.objects.get(id=data["utility_provider_id"])
            if not provider.is_amount_valid(data["amount"]):
                raise serializers.ValidationError(
                    f"Amount must be between {provider.minimum_amount} and {provider.maximum_amount}"
                )
        except UtilityProvider.DoesNotExist:
            pass  # Already handled in field validation

        return data


class SetupRecurringUtilityPaymentSerializer(serializers.Serializer):
    """Serializer for setting up recurring utility payments."""

    utility_provider_id = serializers.UUIDField()
    customer_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    frequency = serializers.ChoiceField(choices=RecurringPaymentFrequency.choices)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(max_length=500, required=False)
    payment_source = serializers.ChoiceField(
        choices=[("wallet", "Wallet"), ("direct", "Direct Payment")], default="wallet"
    )
    spending_limit = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)

    def validate_utility_provider_id(self, value):
        """Validate utility provider exists and is active."""
        try:
            provider = UtilityProvider.objects.get(id=value)
            if not provider.is_active:
                raise serializers.ValidationError("Utility provider is not active")
        except UtilityProvider.DoesNotExist:
            raise serializers.ValidationError("Utility provider not found")
        return value

    def validate(self, data):
        """Validate recurring payment setup data."""
        try:
            provider = UtilityProvider.objects.get(id=data["utility_provider_id"])
            if not provider.is_amount_valid(data["amount"]):
                raise serializers.ValidationError(
                    f"Amount must be between {provider.minimum_amount} and {provider.maximum_amount}"
                )
        except UtilityProvider.DoesNotExist:
            pass  # Already handled in field validation

        if data.get("spending_limit") and data["spending_limit"] < data["amount"]:
            raise serializers.ValidationError(
                "Spending limit cannot be less than payment amount"
            )

        if data.get("end_date") and data.get("start_date"):
            if data["end_date"] <= data["start_date"]:
                raise serializers.ValidationError("End date must be after start date")

        return data
