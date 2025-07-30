"""
Transaction models for ClustR application.
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


class Transaction(AbstractClusterModel):
    """
    Transaction model for tracking all wallet transactions.
    """

    wallet = models.ForeignKey('Wallet',
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
            # Optimized indexes for bill payment queries
            models.Index(fields=["type", "status"]),
            models.Index(fields=["wallet", "type", "status"]),
            models.Index(fields=["created_at", "type"]),
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

    def get_related_bills(self):
        """
        Get all bills related to this transaction.
        
        Returns:
            QuerySet: Bills that use this transaction as payment_transaction
        """
        return self.bills.all()

    def is_bill_payment(self):
        """
        Check if this transaction is a bill payment.
        
        Returns:
            bool: True if this is a bill payment transaction
        """
        return self.type == TransactionType.BILL_PAYMENT or self.bills.exists()

    def get_bill_payment_details(self):
        """
        Get details about the bill(s) this transaction paid for.
        
        Returns:
            dict: Bill payment details including bill types and amounts
        """
        if not self.is_bill_payment():
            return {}
        
        bills = self.get_related_bills()
        if not bills.exists():
            return {}
        
        details = {
            'total_bills': bills.count(),
            'cluster_wide_bills': bills.filter(user_id__isnull=True).count(),
            'user_specific_bills': bills.filter(user_id__isnull=False).count(),
            'total_amount': sum(bill.amount for bill in bills),
            'bills': []
        }
        
        for bill in bills:
            details['bills'].append({
                'id': str(bill.id),
                'bill_number': bill.bill_number,
                'title': bill.title,
                'amount': bill.amount,
                'is_cluster_wide': bill.is_cluster_wide(),
                'user_id': str(bill.user_id) if bill.user_id else None
            })
        
        return details

