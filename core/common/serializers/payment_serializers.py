"""
Payment serializers for ClustR application.
"""

from decimal import Decimal
from rest_framework import serializers
from core.common.models.wallet import (
    Wallet,
    Transaction,
    Bill,
    RecurringPayment,
    WalletStatus,
    PaymentProvider,
    BillType,
    BillStatus,
    RecurringPaymentFrequency,
    PaymentError
)


class PaginationSerializer(serializers.Serializer):
    """Serializer for pagination metadata"""

    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""

    class Meta:
        model = Wallet
        fields = [
            "id",
            "user_id",
            "balance",
            "available_balance",
            "currency",
            "account_number",
            "status",
            "is_pin_set",
            "last_transaction_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "balance",
            "available_balance",
            "is_pin_set",
            "last_transaction_at",
            "created_at",
            "updated_at",
        ]


class WalletBalanceResponseSerializer(serializers.Serializer):
    """Serializer for wallet balance response"""

    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    status = serializers.ChoiceField(choices=WalletStatus.choices)
    is_pin_set = serializers.BooleanField()
    last_transaction_at = serializers.DateTimeField(allow_null=True)

class PaymentErrorSerializer(serializers.ModelSerializer):
    """Serializer for PaymentError model"""

    class Meta:
        model = PaymentError
        fields = [
            "id",
            "transaction_id",
            "error_type",
            "severity",
            "provider_error_code",
            "provider_error_message",
            "user_friendly_message",
            "recovery_options",
            "retry_count",
            "max_retries",
            "can_retry",
            "is_resolved",
            "resolved_at",
            "resolution_method",
            "admin_notified",
            "user_notified",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "transaction_id",
            "created_at",
            "updated_at",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""

    user_id = serializers.UUIDField(source="wallet.user_id", read_only=True)
    failed_payments = PaymentErrorSerializer(many=True, read_only=True, source="failed_payments")

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_id",
            "reference",
            "type",
            "amount",
            "currency",
            "status",
            "description",
            "provider",
            "user_id",
            "created_at",
            "processed_at",
            "failed_at",
            "failure_reason",
            "failed_payments",
            "metadata",
        ]
        read_only_fields = [
            "id",
            "transaction_id",
            "user_id",
            "created_at",
            "processed_at",
            "failed_at",
        ]


class BillSerializer(serializers.ModelSerializer):
    """Serializer for Bill model"""

    remaining_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "user_id",
            "title",
            "description",
            "type",
            "amount",
            "currency",
            "status",
            "acknowledged_at",
            "acknowledged_by",
            "dispute_reason",
            "disputed_at",
            "due_date",
            "paid_amount",
            "paid_at",
            "remaining_amount",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "bill_number",
            "acknowledged_at",
            "acknowledged_by",
            "disputed_at",
            "paid_amount",
            "paid_at",
            "remaining_amount",
            "is_overdue",
            "created_at",
            "updated_at",
        ]


class RecurringPaymentSerializer(serializers.ModelSerializer):
    """Serializer for RecurringPayment model"""

    bill_title = serializers.CharField(source="bill.title", read_only=True)
    bill_amount = serializers.DecimalField(source="bill.amount", max_digits=15, decimal_places=2, read_only=True)
    bill_status = serializers.CharField(source="bill.status", read_only=True)
    utility_provider_name = serializers.CharField(source="utility_provider.name", read_only=True)

    class Meta:
        model = RecurringPayment
        fields = [
            "id",
            "user_id",
            "bill",
            "bill_title",
            "bill_amount", 
            "bill_status",
            "wallet",
            "title",
            "description",
            "amount",
            "currency",
            "frequency",
            "status",
            "start_date",
            "end_date",
            "next_payment_date",
            "last_payment_date",
            "total_payments",
            "failed_attempts",
            "max_failed_attempts",
            "utility_provider",
            "utility_provider_name",
            "customer_id",
            "payment_source",
            "spending_limit",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "bill_title",
            "bill_amount",
            "bill_status",
            "utility_provider_name",
            "next_payment_date",
            "last_payment_date",
            "total_payments",
            "failed_attempts",
            "created_at",
            "updated_at",
        ]


# Input Serializers
class WalletDepositSerializer(serializers.Serializer):
    """Serializer for wallet deposit requests"""

    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    provider = serializers.ChoiceField(
        choices=PaymentProvider.choices, default=PaymentProvider.PAYSTACK
    )
    callback_url = serializers.URLField(required=False, allow_blank=True)


class BillAcknowledgeSerializer(serializers.Serializer):
    """Serializer for bill acknowledgment requests"""

    bill_id = serializers.UUIDField()


class BillDisputeSerializer(serializers.Serializer):
    """Serializer for bill dispute requests"""

    bill_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=1000)


class BillPaymentSerializer(serializers.Serializer):
    """Serializer for bill payment requests"""

    bill_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False
    )


class DirectBillPaymentSerializer(serializers.Serializer):
    """Serializer for direct bill payment requests"""

    bill_id = serializers.UUIDField()
    provider = serializers.ChoiceField(
        choices=PaymentProvider.choices, default=PaymentProvider.PAYSTACK
    )
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    callback_url = serializers.URLField(required=False, allow_blank=True)


class CreateBillSerializer(serializers.Serializer):
    """Serializer for creating bills"""

    user_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )
    type = serializers.ChoiceField(choices=BillType.choices)
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    due_date = serializers.DateTimeField()
    metadata = serializers.JSONField(required=False)


class BulkBillsSerializer(serializers.Serializer):
    """Serializer for bulk bill creation"""

    bills = CreateBillSerializer(many=True)


class UpdateBillStatusSerializer(serializers.Serializer):
    """Serializer for updating bill status"""

    bill_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=BillStatus.choices)


class CreateRecurringPaymentSerializer(serializers.Serializer):
    """Serializer for creating recurring payments"""

    bill_id = serializers.UUIDField(required=False, allow_null=True)
    wallet_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    frequency = serializers.ChoiceField(choices=RecurringPaymentFrequency.choices)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    utility_provider_id = serializers.UUIDField(required=False, allow_null=True)
    customer_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    payment_source = serializers.ChoiceField(
        choices=[("wallet", "Wallet"), ("direct", "Direct Payment")],
        default="wallet"
    )
    spending_limit = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False, allow_null=True
    )
    metadata = serializers.JSONField(required=False)


class PauseRecurringPaymentSerializer(serializers.Serializer):
    """Serializer for pausing recurring payments"""

    payment_id = serializers.UUIDField()


class UpdateRecurringPaymentSerializer(serializers.Serializer):
    """Serializer for updating recurring payments"""

    payment_id = serializers.UUIDField()
    bill_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    frequency = serializers.ChoiceField(choices=RecurringPaymentFrequency.choices, required=False)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    utility_provider_id = serializers.UUIDField(required=False, allow_null=True)
    customer_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    spending_limit = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"), required=False, allow_null=True
    )
    metadata = serializers.JSONField(required=False)


class ResumeRecurringPaymentSerializer(serializers.Serializer):
    """Serializer for resuming recurring payments"""

    payment_id = serializers.UUIDField()


class CancelRecurringPaymentSerializer(serializers.Serializer):
    """Serializer for cancelling recurring payments"""

    payment_id = serializers.UUIDField()


class ClusterWalletTransferSerializer(serializers.Serializer):
    """Serializer for cluster wallet transfers"""

    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(max_length=500)
    recipient_account = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )


class ClusterWalletCreditSerializer(serializers.Serializer):
    """Serializer for cluster wallet credit"""

    amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(max_length=500)
    source = serializers.CharField(max_length=100, default="manual")


# Response Serializers
class DepositResponseSerializer(serializers.Serializer):
    """Serializer for deposit response"""

    transaction_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    provider = serializers.CharField()
    payment_url = serializers.URLField()
    reference = serializers.CharField()


class BillPaymentResponseSerializer(serializers.Serializer):
    """Serializer for bill payment response"""

    transaction_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    bill_id = serializers.UUIDField()
    bill_status = serializers.CharField()
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    wallet_balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class TransactionListResponseSerializer(serializers.Serializer):
    """Serializer for transaction list response"""

    transactions = TransactionSerializer(many=True)
    pagination = PaginationSerializer()


class BillListResponseSerializer(serializers.Serializer):
    """Serializer for bill list response"""

    bills = BillSerializer(many=True)
    pagination = PaginationSerializer()


class RecurringPaymentListResponseSerializer(serializers.Serializer):
    """Serializer for recurring payment list response"""

    recurring_payments = RecurringPaymentSerializer(many=True)
    pagination = PaginationSerializer()


class PaymentStatisticsSerializer(serializers.Serializer):
    """Serializer for payment statistics"""

    total_wallets = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    total_bills = serializers.IntegerField()
    total_recurring_payments = serializers.IntegerField()
    total_transaction_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_pending_bills_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2
    )


class ClusterWalletInfoSerializer(serializers.Serializer):
    """Serializer for cluster wallet info"""

    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.CharField()
    last_transaction_at = serializers.DateTimeField(allow_null=True)


class ClusterRevenueSerializer(serializers.Serializer):
    """Serializer for cluster revenue"""

    period_days = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    bill_payment_count = serializers.IntegerField()
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transactions_count = serializers.IntegerField()


class PaymentDashboardSerializer(serializers.Serializer):
    """Serializer for payment dashboard"""

    statistics = PaymentStatisticsSerializer()
    cluster_wallet = ClusterWalletInfoSerializer()
    cluster_revenue = ClusterRevenueSerializer()
    recent_transactions = TransactionSerializer(many=True)
    recent_bills = BillSerializer(many=True)
    error_summary = serializers.JSONField()


class ClusterWalletAnalyticsSerializer(serializers.Serializer):
    """Serializer for cluster wallet analytics"""

    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_deposits = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_withdrawals = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    bill_payment_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    bill_payment_count = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    last_transaction_at = serializers.DateTimeField(allow_null=True)
    wallet_created_at = serializers.DateTimeField(allow_null=True)


class ClusterWalletResponseSerializer(serializers.Serializer):
    """Serializer for cluster wallet response"""

    analytics = ClusterWalletAnalyticsSerializer()
    recent_transactions = TransactionSerializer(many=True)
