"""
Wallet and payment models for ClustR application.
"""

import uuid
import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger("clustr")


class WalletStatus(models.TextChoices):
    """Wallet status choices"""

    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    CLOSED = "closed", _("Closed")


class TransactionType(models.TextChoices):
    """Transaction type choices"""

    DEPOSIT = "deposit", _("Deposit")
    WITHDRAWAL = "withdrawal", _("Withdrawal")
    PAYMENT = "payment", _("Payment")
    REFUND = "refund", _("Refund")
    TRANSFER = "transfer", _("Transfer")
    BILL_PAYMENT = "bill_payment", _("Bill Payment")


class TransactionStatus(models.TextChoices):
    """Transaction status choices"""

    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED = "refunded", _("Refunded")


class PaymentProvider(models.TextChoices):
    """Payment provider choices"""

    PAYSTACK = "paystack", _("Paystack")
    FLUTTERWAVE = "flutterwave", _("Flutterwave")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    CASH = "cash", _("Cash")


class BillType(models.TextChoices):
    """Bill type choices"""

    # Existing cluster-based bills
    ELECTRICITY = "electricity", _("Electricity")
    WATER = "water", _("Water")
    SECURITY = "security", _("Security")
    MAINTENANCE = "maintenance", _("Maintenance")
    SERVICE_CHARGE = "service_charge", _("Service Charge")
    WASTE_MANAGEMENT = "waste_management", _("Waste Management")

    # New utility bills (user-managed)
    ELECTRICITY_UTILITY = "electricity_utility", _("Electricity (Direct)")
    WATER_UTILITY = "water_utility", _("Water (Direct)")
    INTERNET_UTILITY = "internet_utility", _("Internet")
    CABLE_TV_UTILITY = "cable_tv_utility", _("Cable TV")
    OTHER = "other", _("Other")


class BillStatus(models.TextChoices):
    """Bill status choices"""

    DRAFT = "draft", _("Draft")
    PENDING_ACKNOWLEDGMENT = "pending_acknowledgment", _("Pending Acknowledgment")
    ACKNOWLEDGED = "acknowledged", _("Acknowledged")
    DISPUTED = "disputed", _("Disputed")
    PENDING = "pending", _("Pending Payment")
    OVERDUE = "overdue", _("Overdue")
    PAID = "paid", _("Paid")
    PARTIALLY_PAID = "partially_paid", _("Partially Paid")
    CANCELLED = "cancelled", _("Cancelled")


class RecurringPaymentStatus(models.TextChoices):
    """Recurring payment status choices"""

    ACTIVE = "active", _("Active")
    PAUSED = "paused", _("Paused")
    CANCELLED = "cancelled", _("Cancelled")
    EXPIRED = "expired", _("Expired")


class RecurringPaymentFrequency(models.TextChoices):
    """Recurring payment frequency choices"""

    DAILY = "daily", _("Daily")
    WEEKLY = "weekly", _("Weekly")
    MONTHLY = "monthly", _("Monthly")
    QUARTERLY = "quarterly", _("Quarterly")
    YEARLY = "yearly", _("Yearly")


class BillCategory(models.TextChoices):
    """Bill category choices"""

    CLUSTER_MANAGED = "cluster_managed", _("Cluster Managed")
    USER_MANAGED = "user_managed", _("User Managed")


class PaymentErrorType(models.TextChoices):
    """Payment error type choices"""

    INSUFFICIENT_FUNDS = "insufficient_funds", _("Insufficient Funds")
    INVALID_CARD = "invalid_card", _("Invalid Card")
    EXPIRED_CARD = "expired_card", _("Expired Card")
    DECLINED_CARD = "declined_card", _("Declined Card")
    NETWORK_ERROR = "network_error", _("Network Error")
    PROVIDER_ERROR = "provider_error", _("Provider Error")
    VALIDATION_ERROR = "validation_error", _("Validation Error")
    TIMEOUT_ERROR = "timeout_error", _("Timeout Error")
    AUTHENTICATION_ERROR = "authentication_error", _("Authentication Error")
    LIMIT_EXCEEDED = "limit_exceeded", _("Limit Exceeded")
    ACCOUNT_SUSPENDED = "account_suspended", _("Account Suspended")
    UNKNOWN_ERROR = "unknown_error", _("Unknown Error")
    # Utility-specific errors
    UTILITY_PROVIDER_ERROR = "utility_provider_error", _("Utility Provider Error")
    INVALID_CUSTOMER_ID = "invalid_customer_id", _("Invalid Customer ID")
    UTILITY_SERVICE_UNAVAILABLE = "utility_service_unavailable", _(
        "Utility Service Unavailable"
    )
    METER_NOT_FOUND = "meter_not_found", _("Meter Not Found")
    CUSTOMER_VALIDATION_FAILED = "customer_validation_failed", _(
        "Customer Validation Failed"
    )


class PaymentErrorSeverity(models.TextChoices):
    """Payment error severity choices"""

    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class UtilityProvider(AbstractClusterModel):
    """
    Utility provider model for managing external utility service providers.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        help_text=_("Utility provider name"),
    )

    provider_type = models.CharField(
        verbose_name=_("provider type"),
        max_length=20,
        choices=BillType.choices,
        help_text=_("Type of utility service provided"),
    )

    api_provider = models.CharField(
        verbose_name=_("API provider"),
        max_length=20,
        choices=PaymentProvider.choices,
        help_text=_("Payment API provider (Paystack/Flutterwave)"),
    )

    provider_code = models.CharField(
        verbose_name=_("provider code"),
        max_length=50,
        help_text=_("Unique provider code for API calls (e.g., 'ikeja-electric')"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether this provider is currently active"),
    )

    supports_validation = models.BooleanField(
        verbose_name=_("supports validation"),
        default=True,
        help_text=_("Whether this provider supports customer validation"),
    )

    supports_info_lookup = models.BooleanField(
        verbose_name=_("supports info lookup"),
        default=True,
        help_text=_("Whether this provider supports customer info lookup"),
    )

    minimum_amount = models.DecimalField(
        verbose_name=_("minimum amount"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Minimum payment amount"),
    )

    maximum_amount = models.DecimalField(
        verbose_name=_("maximum amount"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("100000.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Maximum payment amount"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional provider metadata and configuration"),
    )

    class Meta:
        verbose_name = _("Utility Provider")
        verbose_name_plural = _("Utility Providers")
        unique_together = [["provider_code", "api_provider", "cluster"]]
        indexes = [
            models.Index(fields=["provider_type", "cluster"]),
            models.Index(fields=["api_provider"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"

    def is_amount_valid(self, amount):
        """Check if the payment amount is within provider limits."""
        return self.minimum_amount <= amount <= self.maximum_amount


class Wallet(AbstractClusterModel):
    """
    User wallet model for managing balances and payment information.
    """

    user_id = models.UUIDField(
        verbose_name=_("user id"),
        help_text=_("The ID of the user who owns this wallet"),
    )

    balance = models.DecimalField(
        verbose_name=_("balance"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Current wallet balance"),
    )

    available_balance = models.DecimalField(
        verbose_name=_("available balance"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Available balance (excluding pending transactions)"),
    )

    currency = models.CharField(
        verbose_name=_("currency"),
        max_length=3,
        default="NGN",
        help_text=_("Currency code (e.g., NGN, USD)"),
    )

    account_number = models.CharField(
        verbose_name=_("account number"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Associated bank account number"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=WalletStatus.choices,
        default=WalletStatus.ACTIVE,
        help_text=_("Current wallet status"),
    )

    pin_hash = models.CharField(
        verbose_name=_("PIN hash"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Hashed wallet PIN for transactions"),
    )

    is_pin_set = models.BooleanField(
        verbose_name=_("is PIN set"),
        default=False,
        help_text=_("Whether the user has set a wallet PIN"),
    )

    last_transaction_at = models.DateTimeField(
        verbose_name=_("last transaction date"),
        null=True,
        blank=True,
        help_text=_("Date and time of the last transaction"),
    )

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        unique_together = [["user_id", "cluster"]]
        indexes = [
            models.Index(fields=["user_id", "cluster"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Wallet for User {self.user_id} - {self.currency} {self.balance}"

    def update_balance(self, amount, transaction_type):
        """
        Update wallet balance based on transaction type.

        Args:
            amount: Amount to add/subtract
            transaction_type: Type of transaction (deposit, withdrawal, etc.)
        """
        if transaction_type in [TransactionType.DEPOSIT, TransactionType.REFUND]:
            self.balance += amount
            self.available_balance += amount
        elif transaction_type in [
            TransactionType.WITHDRAWAL,
            TransactionType.PAYMENT,
            TransactionType.BILL_PAYMENT,
        ]:
            self.balance -= amount
            self.available_balance -= amount

        self.last_transaction_at = timezone.now()
        self.save(update_fields=["balance", "available_balance", "last_transaction_at"])

    def has_sufficient_balance(self, amount):
        """
        Check if wallet has sufficient balance for a transaction.

        Args:
            amount: Amount to check

        Returns:
            bool: True if sufficient balance, False otherwise
        """
        return self.available_balance >= amount

    def freeze_amount(self, amount):
        """
        Freeze an amount from available balance for pending transactions.

        Args:
            amount: Amount to freeze
        """
        if self.has_sufficient_balance(amount):
            self.available_balance -= amount
            self.save(update_fields=["available_balance"])
            return True
        return False

    def unfreeze_amount(self, amount):
        """
        Unfreeze an amount back to available balance.

        Args:
            amount: Amount to unfreeze
        """
        self.available_balance += amount
        self.save(update_fields=["available_balance"])


class Transaction(AbstractClusterModel):
    """
    Transaction model for tracking all wallet transactions.
    """

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("wallet"),
        help_text=_("The wallet this transaction belongs to"),
    )

    transaction_id = models.CharField(
        verbose_name=_("transaction ID"),
        max_length=100,
        unique=True,
        help_text=_("Unique transaction identifier"),
    )

    reference = models.CharField(
        verbose_name=_("reference"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("External reference (e.g., payment gateway reference)"),
    )

    type = models.CharField(
        verbose_name=_("type"),
        max_length=20,
        choices=TransactionType.choices,
        help_text=_("Type of transaction"),
    )

    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Transaction amount"),
    )

    currency = models.CharField(
        verbose_name=_("currency"),
        max_length=3,
        default="NGN",
        help_text=_("Currency code"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
        help_text=_("Current transaction status"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Transaction description"),
    )

    provider = models.CharField(
        verbose_name=_("provider"),
        max_length=20,
        choices=PaymentProvider.choices,
        blank=True,
        null=True,
        help_text=_("Payment provider used"),
    )

    provider_response = models.JSONField(
        verbose_name=_("provider response"),
        blank=True,
        null=True,
        help_text=_("Response from payment provider"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional transaction metadata"),
    )

    processed_at = models.DateTimeField(
        verbose_name=_("processed at"),
        null=True,
        blank=True,
        help_text=_("Date and time when transaction was processed"),
    )

    failed_at = models.DateTimeField(
        verbose_name=_("failed at"),
        null=True,
        blank=True,
        help_text=_("Date and time when transaction failed"),
    )

    failure_reason = models.TextField(
        verbose_name=_("failure reason"),
        blank=True,
        null=True,
        help_text=_("Reason for transaction failure"),
    )

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type.title()} - {self.currency} {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        """Override save to generate transaction ID if not provided."""
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def mark_as_completed(self):
        """Mark transaction as completed and update wallet balance."""
        if self.status == TransactionStatus.PENDING:
            self.status = TransactionStatus.COMPLETED
            self.processed_at = timezone.now()
            self.wallet.update_balance(self.amount, self.type)
            self.save(update_fields=["status", "processed_at"])

    def mark_as_failed(self, reason=None):
        """Mark transaction as failed and unfreeze amount if needed."""
        if self.status in [TransactionStatus.PENDING, TransactionStatus.PROCESSING]:
            self.status = TransactionStatus.FAILED
            self.failed_at = timezone.now()
            self.failure_reason = reason

            # Unfreeze amount for withdrawal/payment transactions
            if self.type in [
                TransactionType.WITHDRAWAL,
                TransactionType.PAYMENT,
                TransactionType.BILL_PAYMENT,
            ]:
                self.wallet.unfreeze_amount(self.amount)

            self.save(update_fields=["status", "failed_at", "failure_reason"])

    @property
    def failed_payments(self):
        return self.payment_errors.filter(is_resolved=False)


class PaymentError(AbstractClusterModel):
    """
    Payment error model for tracking transaction failures and providing user-friendly audit trails.
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="payment_errors",
        verbose_name=_("transaction"),
        help_text=_("The transaction that failed"),
    )

    error_type = models.CharField(
        verbose_name=_("error type"),
        max_length=30,
        choices=PaymentErrorType.choices,
        help_text=_("Categorized error type"),
    )

    severity = models.CharField(
        verbose_name=_("severity"),
        max_length=20,
        choices=PaymentErrorSeverity.choices,
        help_text=_("Error severity level"),
    )

    provider_error_code = models.CharField(
        verbose_name=_("provider error code"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Error code from payment provider"),
    )

    provider_error_message = models.TextField(
        verbose_name=_("provider error message"),
        help_text=_("Original error message from payment provider"),
    )

    user_friendly_message = models.TextField(
        verbose_name=_("user friendly message"),
        help_text=_("User-friendly error message"),
    )

    recovery_options = models.JSONField(
        verbose_name=_("recovery options"),
        blank=True,
        null=True,
        help_text=_("Available recovery options for the user"),
    )

    retry_count = models.PositiveIntegerField(
        verbose_name=_("retry count"),
        default=0,
        help_text=_("Number of retry attempts made"),
    )

    max_retries = models.PositiveIntegerField(
        verbose_name=_("max retries"),
        default=3,
        help_text=_("Maximum number of retry attempts allowed"),
    )

    can_retry = models.BooleanField(
        verbose_name=_("can retry"),
        default=True,
        help_text=_("Whether this error allows retry attempts"),
    )

    is_resolved = models.BooleanField(
        verbose_name=_("is resolved"),
        default=False,
        help_text=_("Whether this error has been resolved"),
    )

    resolved_at = models.DateTimeField(
        verbose_name=_("resolved at"),
        null=True,
        blank=True,
        help_text=_("Date and time when error was resolved"),
    )

    resolution_method = models.CharField(
        verbose_name=_("resolution method"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Method used to resolve the error"),
    )

    admin_notified = models.BooleanField(
        verbose_name=_("admin notified"),
        default=False,
        help_text=_("Whether administrators have been notified"),
    )

    user_notified = models.BooleanField(
        verbose_name=_("user notified"),
        default=False,
        help_text=_("Whether user has been notified"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional error metadata"),
    )

    class Meta:
        verbose_name = _("Payment Error")
        verbose_name_plural = _("Payment Errors")
        indexes = [
            models.Index(fields=["transaction", "created_at"]),
            models.Index(fields=["error_type"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["can_retry", "retry_count"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment Error: {self.error_type} - {self.transaction.transaction_id}"

    def can_be_retried(self):
        """Check if this error can be retried."""
        return (
            self.can_retry
            and self.retry_count < self.max_retries
            and not self.is_resolved
        )

    def increment_retry_count(self):
        """Increment the retry count."""
        self.retry_count += 1
        self.save(update_fields=["retry_count"])

    def mark_as_resolved(self, resolution_method=None):
        """Mark the error as resolved."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if resolution_method:
            self.resolution_method = resolution_method
        self.save(update_fields=["is_resolved", "resolved_at", "resolution_method"])

    def get_next_retry_delay(self):
        """Get the delay before next retry attempt in minutes."""
        # Exponential backoff: 2, 4, 8 minutes
        return min(2**self.retry_count, 30)  # Cap at 30 minutes


class Bill(AbstractClusterModel):
    """
    Bill model for managing estate bills and charges.
    """

    bill_number = models.CharField(
        verbose_name=_("bill number"),
        max_length=50,
        unique=True,
        help_text=_("Unique bill number"),
    )

    user_id = models.UUIDField(
        verbose_name=_("user id"),
        help_text=_("The ID of the user this bill is for"),
    )

    title = models.CharField(
        verbose_name=_("title"),
        max_length=200,
        help_text=_("Bill title"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
        help_text=_("Bill description"),
    )

    type = models.CharField(
        verbose_name=_("type"),
        max_length=20,
        choices=BillType.choices,
        help_text=_("Type of bill"),
    )

    category = models.CharField(
        verbose_name=_("category"),
        max_length=20,
        choices=BillCategory.choices,
        default=BillCategory.CLUSTER_MANAGED,
        help_text=_("Bill category (cluster-managed or user-managed)"),
    )

    utility_provider = models.ForeignKey(
        UtilityProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        verbose_name=_("utility provider"),
        help_text=_("Utility provider for user-managed bills"),
    )

    customer_id = models.CharField(
        verbose_name=_("customer ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Customer ID/meter number for utility bills"),
    )

    is_automated = models.BooleanField(
        verbose_name=_("is automated"),
        default=False,
        help_text=_("Whether this bill has automated recurring payments"),
    )

    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Bill amount"),
    )

    currency = models.CharField(
        verbose_name=_("currency"),
        max_length=3,
        default="NGN",
        help_text=_("Currency code"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=25,
        choices=BillStatus.choices,
        default=BillStatus.PENDING_ACKNOWLEDGMENT,
        help_text=_("Current bill status"),
    )

    acknowledged_at = models.DateTimeField(
        verbose_name=_("acknowledged at"),
        null=True,
        blank=True,
        help_text=_("Date and time when bill was acknowledged by user"),
    )

    acknowledged_by = models.UUIDField(
        verbose_name=_("acknowledged by"),
        null=True,
        blank=True,
        help_text=_("ID of the user who acknowledged this bill"),
    )

    dispute_reason = models.TextField(
        verbose_name=_("dispute reason"),
        blank=True,
        null=True,
        help_text=_("Reason for disputing the bill"),
    )

    disputed_at = models.DateTimeField(
        verbose_name=_("disputed at"),
        null=True,
        blank=True,
        help_text=_("Date and time when bill was disputed"),
    )

    due_date = models.DateTimeField(
        verbose_name=_("due date"),
        help_text=_("Bill due date"),
    )

    paid_amount = models.DecimalField(
        verbose_name=_("paid amount"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Amount already paid"),
    )

    paid_at = models.DateTimeField(
        verbose_name=_("paid at"),
        null=True,
        blank=True,
        help_text=_("Date and time when bill was paid"),
    )

    payment_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        verbose_name=_("payment transaction"),
        help_text=_("Transaction used to pay this bill"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional bill metadata"),
    )

    class Meta:
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")
        indexes = [
            models.Index(fields=["user_id", "cluster"]),
            models.Index(fields=["bill_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.currency} {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        """Override save to generate bill number if not provided."""
        if not self.bill_number:
            self.bill_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if bill is overdue."""
        return self.due_date < timezone.now() and self.status not in [
            BillStatus.PAID,
            BillStatus.CANCELLED,
        ]

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid."""
        return self.amount - self.paid_amount

    def mark_as_paid(self, transaction=None):
        """Mark bill as paid."""
        self.status = BillStatus.PAID
        self.paid_amount = self.amount
        self.paid_at = timezone.now()
        if transaction:
            self.payment_transaction = transaction
        self.save(
            update_fields=["status", "paid_amount", "paid_at", "payment_transaction"]
        )

    def acknowledge(self, acknowledged_by: str):
        """Acknowledge the bill."""
        if self.status == BillStatus.PENDING_ACKNOWLEDGMENT:
            self.status = BillStatus.ACKNOWLEDGED
            self.acknowledged_at = timezone.now()
            self.acknowledged_by = acknowledged_by
            self.save(update_fields=["status", "acknowledged_at", "acknowledged_by"])
            return True
        return False

    def dispute(self, disputed_by: str, reason: str):
        """Dispute the bill."""
        if self.status in [BillStatus.PENDING_ACKNOWLEDGMENT, BillStatus.ACKNOWLEDGED]:
            self.status = BillStatus.DISPUTED
            self.disputed_at = timezone.now()
            self.dispute_reason = reason
            self.last_modified_by = disputed_by
            self.save(
                update_fields=[
                    "status",
                    "disputed_at",
                    "dispute_reason",
                    "last_modified_by",
                ]
            )
            return True
        return False

    def can_be_paid(self):
        """Check if bill can be paid."""
        return self.status in [
            BillStatus.ACKNOWLEDGED,
            BillStatus.PENDING,
            BillStatus.PARTIALLY_PAID,
            BillStatus.OVERDUE,
        ]

    def add_payment(self, amount, transaction=None):
        """Add a partial payment to the bill."""
        if not self.can_be_paid():
            raise ValueError(f"Bill cannot be paid in current status: {self.status}")

        self.paid_amount += amount
        if self.paid_amount >= self.amount:
            self.status = BillStatus.PAID
            self.paid_at = timezone.now()
        else:
            self.status = BillStatus.PARTIALLY_PAID

        if transaction:
            self.payment_transaction = transaction

        self.save(
            update_fields=["paid_amount", "status", "paid_at", "payment_transaction"]
        )

        # Credit the cluster's main wallet immediately after successful bill payment
        self.credit_cluster_wallet(amount, transaction)

    def credit_cluster_wallet(self, amount, transaction=None):
        """Credit the cluster's main wallet with bill payment."""
        from core.common.utils.cluster_wallet_utils import (
            credit_cluster_from_bill_payment,
        )

        credit_cluster_from_bill_payment(self.cluster, amount, self, transaction)

    def is_utility_bill(self):
        """Check if this is a user-managed utility bill."""
        return self.category == BillCategory.USER_MANAGED

    def can_automate_payment(self):
        """Check if this bill can have automated payments."""
        return self.is_utility_bill() and self.utility_provider is not None

    def get_utility_metadata(self):
        """Get utility-specific metadata."""
        if not self.is_utility_bill():
            return {}

        return {
            "customer_id": self.customer_id,
            "provider_name": (
                self.utility_provider.name if self.utility_provider else None
            ),
            "provider_code": (
                self.utility_provider.provider_code if self.utility_provider else None
            ),
            "api_provider": (
                self.utility_provider.api_provider if self.utility_provider else None
            ),
        }


class RecurringPayment(AbstractClusterModel):
    """
    Recurring payment model for scheduled payments.
    """

    user_id = models.UUIDField(
        verbose_name=_("user id"),
        help_text=_("The ID of the user who set up this recurring payment"),
    )

    bill = models.ForeignKey(
        Bill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_payments",
        verbose_name=_("bill"),
        help_text=_("The bill to debit for payments"),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="recurring_payments",
        verbose_name=_("wallet"),
        help_text=_("The wallet to debit for payments"),
    )

    title = models.CharField(
        verbose_name=_("title"),
        max_length=200,
        help_text=_("Recurring payment title"),
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
        null=True,
        help_text=_("Recurring payment description"),
    )

    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Payment amount"),
    )

    currency = models.CharField(
        verbose_name=_("currency"),
        max_length=3,
        default="NGN",
        help_text=_("Currency code"),
    )

    frequency = models.CharField(
        verbose_name=_("frequency"),
        max_length=20,
        choices=RecurringPaymentFrequency.choices,
        help_text=_("Payment frequency"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=RecurringPaymentStatus.choices,
        default=RecurringPaymentStatus.ACTIVE,
        help_text=_("Current recurring payment status"),
    )

    start_date = models.DateTimeField(
        verbose_name=_("start date"),
        help_text=_("Date when recurring payments should start"),
    )

    end_date = models.DateTimeField(
        verbose_name=_("end date"),
        null=True,
        blank=True,
        help_text=_("Date when recurring payments should end (optional)"),
    )

    next_payment_date = models.DateTimeField(
        verbose_name=_("next payment date"),
        help_text=_("Date of the next scheduled payment"),
    )

    last_payment_date = models.DateTimeField(
        verbose_name=_("last payment date"),
        null=True,
        blank=True,
        help_text=_("Date of the last successful payment"),
    )

    total_payments = models.PositiveIntegerField(
        verbose_name=_("total payments"),
        default=0,
        help_text=_("Total number of successful payments made"),
    )

    failed_attempts = models.PositiveIntegerField(
        verbose_name=_("failed attempts"),
        default=0,
        help_text=_("Number of consecutive failed payment attempts"),
    )

    max_failed_attempts = models.PositiveIntegerField(
        verbose_name=_("max failed attempts"),
        default=3,
        help_text=_("Maximum failed attempts before pausing"),
    )

    utility_provider = models.ForeignKey(
        UtilityProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_payments",
        verbose_name=_("utility provider"),
        help_text=_("Utility provider for automated utility payments"),
    )

    customer_id = models.CharField(
        verbose_name=_("customer ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Customer ID/meter number for utility payments"),
    )

    payment_source = models.CharField(
        verbose_name=_("payment source"),
        max_length=20,
        choices=[("wallet", _("Wallet")), ("direct", _("Direct Payment"))],
        default="wallet",
        help_text=_("Source of payment (wallet or direct)"),
    )

    spending_limit = models.DecimalField(
        verbose_name=_("spending limit"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Maximum amount that can be spent per payment"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional recurring payment metadata"),
    )

    class Meta:
        verbose_name = _("Recurring Payment")
        verbose_name_plural = _("Recurring Payments")
        indexes = [
            models.Index(fields=["user_id", "cluster"]),
            models.Index(fields=["status"]),
            models.Index(fields=["next_payment_date"]),
            models.Index(fields=["frequency"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.currency} {self.amount} ({self.frequency})"

    def calculate_next_payment_date(self):
        """Calculate the next payment date based on frequency."""
        from dateutil.relativedelta import relativedelta

        current_date = self.next_payment_date or self.start_date

        if self.frequency == RecurringPaymentFrequency.DAILY:
            return current_date + relativedelta(days=1)
        elif self.frequency == RecurringPaymentFrequency.WEEKLY:
            return current_date + relativedelta(weeks=1)
        elif self.frequency == RecurringPaymentFrequency.MONTHLY:
            return current_date + relativedelta(months=1)
        elif self.frequency == RecurringPaymentFrequency.QUARTERLY:
            return current_date + relativedelta(months=3)
        elif self.frequency == RecurringPaymentFrequency.YEARLY:
            return current_date + relativedelta(years=1)

        return current_date

    def is_utility_payment(self):
        """Check if this is a utility payment."""
        return self.utility_provider is not None

    def process_payment(self):
        """Process the recurring payment."""
        if self.status != RecurringPaymentStatus.ACTIVE:
            return False

        if self.is_utility_payment():
            return self.process_utility_payment()
        else:
            return self.process_cluster_payment()

    def process_cluster_payment(self):
        """Process regular cluster-based recurring payment."""
        if not self.wallet.has_sufficient_balance(self.amount):
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_attempts:
                self.status = RecurringPaymentStatus.PAUSED
            self.save(update_fields=["failed_attempts", "status"])

            # Handle recurring payment failure with error handling
            from core.common.utils.payment_error_utils import PaymentErrorHandler

            PaymentErrorHandler.handle_recurring_payment_failure(
                self, "Insufficient wallet balance"
            )

            return False

        # Create transaction
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self.wallet,
            type=TransactionType.PAYMENT,
            amount=self.amount,
            currency=self.currency,
            description=f"Recurring payment: {self.title}",
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            created_by=self.created_by,
            last_modified_by=self.last_modified_by,
        )

        # Update wallet balance
        self.wallet.update_balance(self.amount, TransactionType.PAYMENT)

        self.bill.credit_cluster_wallet(self.amount, transaction)

        # Update recurring payment
        self.last_payment_date = timezone.now()
        self.next_payment_date = self.calculate_next_payment_date()
        self.total_payments += 1
        self.failed_attempts = 0

        # Check if recurring payment should end
        if self.end_date and self.next_payment_date > self.end_date:
            self.status = RecurringPaymentStatus.EXPIRED

        self.save(
            update_fields=[
                "last_payment_date",
                "next_payment_date",
                "total_payments",
                "failed_attempts",
                "status",
            ]
        )
        return True

    def process_utility_payment(self):
        """Process utility-specific recurring payment."""
        # Check spending limit
        if self.spending_limit and self.amount > self.spending_limit:
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_attempts:
                self.status = RecurringPaymentStatus.PAUSED
            self.save(update_fields=["failed_attempts", "status"])
            return False

        # Check wallet balance
        if not self.wallet.has_sufficient_balance(self.amount):
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_attempts:
                self.status = RecurringPaymentStatus.PAUSED
            self.save(update_fields=["failed_attempts", "status"])
            return False

        try:
            # Process utility payment via service
            from core.common.services.utility_service import UtilityPaymentManager

            result = UtilityPaymentManager.process_utility_payment(
                user_id=self.user_id,
                utility_provider=self.utility_provider,
                customer_id=self.customer_id,
                amount=self.amount,
                wallet=self.wallet,
                description=f"Automated utility payment: {self.title}",
            )

            if result.get("success"):
                # Update recurring payment on success
                self.last_payment_date = timezone.now()
                self.next_payment_date = self.calculate_next_payment_date()
                self.total_payments += 1
                self.failed_attempts = 0

                # Check if recurring payment should end
                if self.end_date and self.next_payment_date > self.end_date:
                    self.status = RecurringPaymentStatus.EXPIRED

                self.save(
                    update_fields=[
                        "last_payment_date",
                        "next_payment_date",
                        "total_payments",
                        "failed_attempts",
                        "status",
                    ]
                )
                return True
            else:
                # Handle failure
                self.failed_attempts += 1
                if self.failed_attempts >= self.max_failed_attempts:
                    self.status = RecurringPaymentStatus.PAUSED
                self.save(update_fields=["failed_attempts", "status"])
                return False

        except Exception as e:
            logger.error(
                f"Utility payment failed for recurring payment {self.id}: {str(e)}"
            )
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_attempts:
                self.status = RecurringPaymentStatus.PAUSED
            self.save(update_fields=["failed_attempts", "status"])
            return False

    def pause(self, paused_by: str = None):
        """Pause the recurring payment."""
        self.status = RecurringPaymentStatus.PAUSED
        self.last_modified_by = paused_by
        self.save(update_fields=["status", "last_modified_by"])

    def resume(self, resumed_by: str = None):
        """Resume the recurring payment."""
        if self.status == RecurringPaymentStatus.PAUSED:
            self.status = RecurringPaymentStatus.ACTIVE
            self.failed_attempts = 0
            self.last_modified_by = resumed_by
            self.save(update_fields=["status", "failed_attempts", "last_modified_by"])

    def cancel(self, cancelled_by: str = None):
        """Cancel the recurring payment."""
        self.status = RecurringPaymentStatus.CANCELLED
        self.last_modified_by = cancelled_by
        self.save(update_fields=["status", "last_modified_by"])
