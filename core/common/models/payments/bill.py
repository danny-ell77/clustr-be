"""
Bill models for ClustR application.
"""

import uuid
import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

# Related model imports (will be converted to string references)
# from core.common.models.unknown import BillCategory

logger = logging.getLogger('clustr')


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

class BillCategory(models.TextChoices):
    """Bill category choices"""

    CLUSTER_MANAGED = "cluster_managed", _("Cluster-managed")
    USER_MANAGED = "user_managed", _("User-managed")


class Bill(AbstractClusterModel):
    """
    Bill model for managing cluster bills and charges.
    Supports both cluster-wide bills (user=null) and user-specific bills (user=specific_user).
    """

    bill_number = models.CharField(
        verbose_name=_("bill number"),
        max_length=50,
        unique=True,
        help_text=_("Unique bill number"),
    )

    user_id = models.UUIDField(
        verbose_name=_("user id"),
        null=True,
        blank=True,
        help_text=_("The ID of the user this bill is for (null for cluster-wide bills)"),
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
        "common.UtilityProvider",
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

    # Status field removed - will be derived from acknowledgments and transactions
    
    acknowledged_by = models.ManyToManyField(
        "accounts.AccountUser",
        blank=True,
        related_name="acknowledged_bills",
        verbose_name=_("acknowledged by"),
        help_text=_("Users who have acknowledged this bill"),
    )

    allow_payment_after_due = models.BooleanField(
        verbose_name=_("allow payment after due"),
        default=True,
        help_text=_("Whether payment is allowed after due date"),
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

    payment_transaction = models.ForeignKey('Transaction',
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
            models.Index(fields=["cluster", "user_id"]),
            models.Index(fields=["bill_number"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["type"]),
            models.Index(fields=["due_date", "allow_payment_after_due"]),
            models.Index(fields=["disputed_at"]),
            models.Index(fields=["paid_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        bill_type = "Estate-wide" if self.user_id is None else "User-specific"
        return f"{self.title} - {self.currency} {self.amount} ({bill_type})"

    def save(self, *args, **kwargs):
        """Override save to generate bill number if not provided."""
        if not self.bill_number:
            self.bill_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def is_cluster_wide(self):
        """Check if this is an cluster-wide bill."""
        return self.user_id is None

    def can_be_acknowledged_by(self, user):
        """Check if a user can acknowledge this bill."""
        if self.is_cluster_wide():
            # Estate-wide bills can be acknowledged by any user in the same cluster
            return hasattr(user, 'cluster') and user.cluster == self.cluster
        else:
            # User-specific bills can only be acknowledged by the target user
            return str(user.id) == str(self.user_id)

    def can_be_paid_by(self, user):
        """Check if a user can pay this bill."""
        # First check if user can acknowledge the bill (same logic)
        if not self.can_be_acknowledged_by(user):
            return False
        
        # Check if bill has been acknowledged by this user
        if not self.acknowledged_by.filter(id=user.id).exists():
            return False
        
        # Check due date restrictions
        if self.is_overdue and not self.allow_payment_after_due:
            return False
        
        return True

    @property
    def is_overdue(self):
        """Check if bill is overdue."""
        return self.due_date < timezone.now() and not self.is_fully_paid

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid."""
        return self.amount - self.paid_amount

    @property
    def is_fully_paid(self):
        """Check if bill is fully paid."""
        return self.paid_amount >= self.amount

    @property
    def is_disputed(self):
        """Check if bill is disputed."""
        return self.disputed_at is not None

    @property
    def acknowledgment_count(self):
        """Get the number of users who have acknowledged this bill."""
        return self.acknowledged_by.count()

    def is_acknowledged_by(self, user):
        """Check if a specific user has acknowledged this bill."""
        return self.acknowledged_by.filter(id=user.id).exists()

    def get_acknowledging_users(self):
        """Get all users who have acknowledged this bill."""
        return self.acknowledged_by.all()

    def remove_acknowledgment(self, user):
        """
        Remove acknowledgment from a user (for admin purposes).
        
        Args:
            user: AccountUser instance to remove acknowledgment from
            
        Returns:
            bool: True if acknowledgment was removed, False if user hadn't acknowledged
        """
        if self.acknowledged_by.filter(id=user.id).exists():
            self.acknowledged_by.remove(user)
            return True
        return False

    def mark_as_paid(self, transaction=None):
        """Mark bill as paid."""
        self.paid_amount = self.amount
        self.paid_at = timezone.now()
        if transaction:
            self.payment_transaction = transaction
            # Ensure transaction type is set correctly for bill payments
            if transaction.type != TransactionType.BILL_PAYMENT:
                transaction.type = TransactionType.BILL_PAYMENT
                transaction.save(update_fields=['type'])
        self.save(
            update_fields=["paid_amount", "paid_at", "payment_transaction"]
        )

    def acknowledge(self, user):
        """
        Acknowledge the bill by adding user to acknowledged_by ManyToMany field.
        
        Args:
            user: AccountUser instance acknowledging the bill
            
        Returns:
            bool: True if acknowledgment was successful, False otherwise
        """
        # Check if user can acknowledge this bill
        if not self.can_be_acknowledged_by(user):
            return False
            
        # Check if user has already acknowledged
        if self.acknowledged_by.filter(id=user.id).exists():
            return False  # Already acknowledged
            
        # Add user to acknowledged_by ManyToMany field
        self.acknowledged_by.add(user)
        return True

    def dispute(self, user, reason: str):
        """
        Dispute the bill.
        
        Args:
            user: AccountUser instance disputing the bill
            reason: Reason for disputing the bill
            
        Returns:
            bool: True if dispute was successful, False otherwise
        """
        # Check if user can dispute this bill (same logic as acknowledgment)
        if not self.can_be_acknowledged_by(user):
            return False
            
        # Check if bill is not already fully paid
        if self.is_fully_paid:
            return False
            
        self.disputed_at = timezone.now()
        self.dispute_reason = reason
        self.save(
            update_fields=[
                "disputed_at",
                "dispute_reason",
            ]
        )
        return True

    def can_be_paid(self):
        """Check if bill can be paid."""
        # Bill can be paid if it's not fully paid and not disputed
        return not self.is_fully_paid and self.disputed_at is None

    def add_payment(self, amount, transaction=None):
        """Add a partial payment to the bill."""
        if not self.can_be_paid():
            raise ValueError("Bill cannot be paid - either fully paid or disputed")

        self.paid_amount += amount
        if self.paid_amount >= self.amount:
            self.paid_at = timezone.now()

        if transaction:
            self.payment_transaction = transaction
            # Ensure transaction type is set correctly for bill payments
            if transaction.type != TransactionType.BILL_PAYMENT:
                transaction.type = TransactionType.BILL_PAYMENT
                transaction.save(update_fields=['type'])

        self.save(
            update_fields=["paid_amount", "paid_at", "payment_transaction"]
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

    def can_be_paid_by_transaction(self, transaction):
        """
        Check if this bill can be paid by a specific transaction.
        
        Args:
            transaction: Transaction instance
            
        Returns:
            bool: True if transaction can pay this bill
        """
        # Basic validation
        if not self.can_be_paid():
            return False
        
        # Check if transaction amount is sufficient for remaining amount
        if transaction.amount < self.remaining_amount:
            return False
        
        # Check if transaction is from the correct user for user-specific bills
        if not self.is_cluster_wide():
            # For user-specific bills, transaction wallet must belong to the target user
            if str(transaction.wallet.user_id) != str(self.user_id):
                return False
        else:
            # For cluster-wide bills, transaction wallet user must be from the same cluster
            # This would require checking the user's cluster, but we don't have direct access
            # to the User model here. This validation should be done at the business logic level.
            pass
        
        return True

    def link_transaction(self, transaction):
        """
        Link a transaction to this bill as payment.
        
        Args:
            transaction: Transaction instance to link
            
        Returns:
            bool: True if linking was successful
        """
        if not self.can_be_paid_by_transaction(transaction):
            return False
        
        # Link the transaction
        self.payment_transaction = transaction
        
        # Update payment details
        payment_amount = min(transaction.amount, self.remaining_amount)
        self.add_payment(payment_amount, transaction)
        
        return True

