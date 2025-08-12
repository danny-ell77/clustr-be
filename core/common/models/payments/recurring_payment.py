"""
Recurring Payment models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


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


class RecurringPayment(AbstractClusterModel):
    """
    Recurring payment model for scheduled payments.
    """

    user_id = models.UUIDField(
        verbose_name=_("user id"),
        help_text=_("The ID of the user who set up this recurring payment"),
    )

    bill = models.ForeignKey('Bill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_payments",
        verbose_name=_("bill"),
        help_text=_("The bill to debit for payments"),
    )

    wallet = models.ForeignKey('Wallet',
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
        "common.UtilityProvider",
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
        default_permissions = []
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
            from core.common.includes.payment_error_utils import PaymentErrorHandler

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
            from core.common.includes import utilities

            # Pass metadata from recurring payment to the payment processor
            payment_kwargs = self.metadata or {}

            result = utilities.process_utility_payment(
                user_id=self.user_id,
                utility_provider=self.utility_provider,
                customer_id=self.customer_id,
                amount=self.amount,
                wallet=self.wallet,
                description=f"Automated utility payment: {self.title}",
                **payment_kwargs,
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