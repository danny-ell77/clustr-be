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

logger = logging.getLogger('clustr')


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
    ELECTRICITY = "electricity", _("Electricity")
    WATER = "water", _("Water")
    SECURITY = "security", _("Security")
    MAINTENANCE = "maintenance", _("Maintenance")
    SERVICE_CHARGE = "service_charge", _("Service Charge")
    WASTE_MANAGEMENT = "waste_management", _("Waste Management")
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
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_("Current wallet balance"),
    )
    
    available_balance = models.DecimalField(
        verbose_name=_("available balance"),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
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
            amount: Transaction amount
            transaction_type: Type of transaction
        """
        if transaction_type in [TransactionType.DEPOSIT, TransactionType.REFUND]:
            self.balance += amount
            self.available_balance += amount
        elif transaction_type in [TransactionType.WITHDRAWAL, TransactionType.PAYMENT, TransactionType.BILL_PAYMENT]:
            self.balance -= amount
            self.available_balance -= amount
        
        self.last_transaction_at = timezone.now()
        self.save()

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
            self.save()
            return True
        return False

    def unfreeze_amount(self, amount):
        """
        Unfreeze an amount back to available balance.
        
        Args:
            amount: Amount to unfreeze
        """
        self.available_balance += amount
        self.save()


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
        validators=[MinValueValidator(Decimal('0.01'))],
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
            self.save()

    def mark_as_failed(self, reason=None):
        """Mark transaction as failed and unfreeze amount if needed."""
        if self.status in [TransactionStatus.PENDING, TransactionStatus.PROCESSING]:
            self.status = TransactionStatus.FAILED
            self.failed_at = timezone.now()
            self.failure_reason = reason
            
            # Unfreeze amount for withdrawal/payment transactions
            if self.type in [TransactionType.WITHDRAWAL, TransactionType.PAYMENT, TransactionType.BILL_PAYMENT]:
                self.wallet.unfreeze_amount(self.amount)
            
            self.save()


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
    
    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
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
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
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
        return self.due_date < timezone.now() and self.status not in [BillStatus.PAID, BillStatus.CANCELLED]

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
        self.save()

    def acknowledge(self, acknowledged_by: str):
        """Acknowledge the bill."""
        if self.status == BillStatus.PENDING_ACKNOWLEDGMENT:
            self.status = BillStatus.ACKNOWLEDGED
            self.acknowledged_at = timezone.now()
            self.acknowledged_by = acknowledged_by
            self.save()
            return True
        return False
    
    def dispute(self, disputed_by: str, reason: str):
        """Dispute the bill."""
        if self.status in [BillStatus.PENDING_ACKNOWLEDGMENT, BillStatus.ACKNOWLEDGED]:
            self.status = BillStatus.DISPUTED
            self.disputed_at = timezone.now()
            self.dispute_reason = reason
            self.last_modified_by = disputed_by
            self.save()
            return True
        return False
    
    def can_be_paid(self):
        """Check if bill can be paid."""
        return self.status in [BillStatus.ACKNOWLEDGED, BillStatus.PENDING, BillStatus.PARTIALLY_PAID, BillStatus.OVERDUE]
    
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
        
        self.save()
        
        # Credit the cluster's main wallet immediately after successful bill payment
        self._credit_cluster_wallet(amount, transaction)
    
    def _credit_cluster_wallet(self, amount, transaction=None):
        """Credit the cluster's main wallet with bill payment."""
        from core.common.utils.cluster_wallet_utils import credit_cluster_from_bill_payment
        credit_cluster_from_bill_payment(self.cluster, amount, self, transaction)


class RecurringPayment(AbstractClusterModel):
    """
    Recurring payment model for scheduled payments.
    """
    
    user_id = models.UUIDField(
        verbose_name=_("user id"),
        help_text=_("The ID of the user who set up this recurring payment"),
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
        validators=[MinValueValidator(Decimal('0.01'))],
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

    def process_payment(self):
        """Process the recurring payment."""
        if self.status != RecurringPaymentStatus.ACTIVE:
            return False
        
        if not self.wallet.has_sufficient_balance(self.amount):
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_attempts:
                self.status = RecurringPaymentStatus.PAUSED
            self.save()
            
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
        
        # Update recurring payment
        self.last_payment_date = timezone.now()
        self.next_payment_date = self.calculate_next_payment_date()
        self.total_payments += 1
        self.failed_attempts = 0
        
        # Check if recurring payment should end
        if self.end_date and self.next_payment_date > self.end_date:
            self.status = RecurringPaymentStatus.EXPIRED
        
        self.save()
        return True

    def pause(self):
        """Pause the recurring payment."""
        self.status = RecurringPaymentStatus.PAUSED
        self.save()

    def resume(self):
        """Resume the recurring payment."""
        if self.status == RecurringPaymentStatus.PAUSED:
            self.status = RecurringPaymentStatus.ACTIVE
            self.failed_attempts = 0
            self.save()

    def cancel(self):
        """Cancel the recurring payment."""
        self.status = RecurringPaymentStatus.CANCELLED
        self.save()