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
from django.contrib.auth import get_user_model

from core.common.models.base import AbstractClusterModel

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


class DisputeStatus(models.TextChoices):
    """Dispute status choices"""

    OPEN = "open", _("Open")
    UNDER_REVIEW = "under_review", _("Under Review")
    RESOLVED = "resolved", _("Resolved")
    REJECTED = "rejected", _("Rejected")
    WITHDRAWN = "withdrawn", _("Withdrawn")


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

    created_by_user = models.BooleanField(
        default=False,
        help_text=_("Indicates if the bill was created by the user themselves, not an admin.")
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
        default_permissions = []
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")
        indexes = [
            models.Index(fields=["cluster", "user_id"]),
            models.Index(fields=["bill_number"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["type"]),
            models.Index(fields=["due_date", "allow_payment_after_due"]),
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
        # First, check if the user is the intended recipient (or in the cluster)
        if not self.can_be_acknowledged_by(user):
            return False

        # For user-managed bills, they must be acknowledged first
        if self.category == BillCategory.USER_MANAGED:
            if not self.acknowledged_by.filter(id=user.id).exists():
                return False

        # Check due date restrictions
        is_past_due = self.due_date < timezone.now()
        if is_past_due and not self.allow_payment_after_due:
            return False

        return True

    @property
    def is_overdue(self):
        """Check if bill is overdue."""
        return self.user_id and self.due_date < timezone.now() and not self.is_fully_paid

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid."""
        return self.user_id and self.amount - self.paid_amount

    @property
    def is_fully_paid(self):
        """Check if bill is fully paid."""
        return self.user_id and self.paid_amount >= self.amount

    @property
    def is_disputed(self):
        """Check if bill has any active disputes."""
        return self.user_id and self.disputes.filter(status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]).exists()

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
        """
        Mark a USER_MANAGED bill as fully paid.
        This method should NOT be used for CLUSTER_MANAGED bills.
        """
        if self.category == BillCategory.CLUSTER_MANAGED:
            logger.warning(
                f"Attempted to use mark_as_paid on a CLUSTER_MANAGED bill (ID: {self.id}). "
                f"This method is only for USER_MANAGED bills."
            )
            return

        self.paid_amount = self.amount
        self.paid_at = timezone.now()
        if transaction:
            self.payment_transaction = transaction
            # Ensure transaction type is set correctly for bill payments
            from .transaction import TransactionType
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
        if not self.can_be_acknowledged_by(user):
            return False
            
        if self.acknowledged_by.filter(id=user.id).exists():
            return False  # Already acknowledged
            
        self.acknowledged_by.add(user)
        return True

    def dispute(self, user, reason: str):
        """
        Create a dispute for this bill.
        
        Args:
            user: AccountUser instance disputing the bill
            reason: Reason for disputing the bill
            
        Returns:
            BillDispute instance if successful, None otherwise
        """
        if not self.can_be_acknowledged_by(user):
            return None
            
        if self.is_fully_paid:
            return None
        
        # Check if user already has an active dispute for this bill
        existing_dispute = self.disputes.filter(
            disputed_by=user,
            status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
        ).first()
        
        if existing_dispute:
            return existing_dispute
            
        # Create new dispute
        dispute = BillDispute.objects.create(
            bill=self,
            disputed_by=user,
            reason=reason,
            cluster=self.cluster
        )
        return dispute

    def can_be_paid(self):
        """
        Check if the bill can be paid.
        A bill can be paid if it is not fully paid and has no active disputes.
        Uses the correct property based on the bill category.
        """
        if self.category == BillCategory.CLUSTER_MANAGED:
            is_paid = self.is_fully_paid_cluster
        else:
            is_paid = self.is_fully_paid

        return not is_paid and not self.is_disputed

    def add_payment(self, amount, transaction):
        """
        Handles the logic for adding a payment to a bill.

        For USER_MANAGED bills, it updates the bill's state directly.
        For CLUSTER_MANAGED bills, it only handles post-payment actions like
        crediting the cluster wallet. The transaction itself is the record of payment.
        """
        User = get_user_model()
        user = User.objects.filter(pk=transaction.wallet.user_id).first()
        if not user:
            logger.error(f"Cannot find user associated with transaction {transaction.id}")
            return

        # Logic for user-managed bills (explicit, single-payer)
        if self.category == BillCategory.USER_MANAGED:
            if not self.can_be_paid_by(user):
                raise ValueError("Bill cannot be paid by this user - check acknowledgment, due date, or dispute status.")

            self.paid_amount += amount
            if self.paid_amount >= self.amount:
                self.paid_at = timezone.now()

            self.payment_transaction = transaction
            from .transaction import TransactionType
            if transaction.type != TransactionType.BILL_PAYMENT:
                transaction.type = TransactionType.BILL_PAYMENT
                transaction.save(update_fields=['type'])
            
            self.save(update_fields=["paid_amount", "paid_at", "payment_transaction"])

        # Logic for cluster-managed bills (multi-payer)
        elif self.category == BillCategory.CLUSTER_MANAGED:
            # For cluster bills, we don't modify the bill's state upon payment.
            # The transaction record is the source of truth.
            # We just need to ensure the user was eligible to pay.
            if not self.acknowledged_by.filter(id=user.id).exists():
                raise ValueError("User must acknowledge a cluster bill before paying.")

        # Credit the cluster's main wallet immediately after any successful bill payment
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

    def get_active_disputes(self):
        """Get all active disputes for this bill."""
        return self.disputes.filter(status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW])

    def get_user_dispute(self, user):
        """Get active dispute by a specific user."""
        return self.disputes.filter(
            disputed_by=user,
            status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
        ).first()

    def has_dispute_by_user(self, user):
        """Check if a specific user has an active dispute for this bill."""
        return self.get_user_dispute(user) is not None

    @property
    def dispute_count(self):
        """Get the number of active disputes for this bill."""
        return self.get_active_disputes().count()

    # --- Properties and Methods for Cluster-Managed Bill Logic ---

    @property
    def total_paid_amount_cluster(self):
        """
        Calculates the total amount paid towards a CLUSTER_MANAGED bill
        by aggregating all related successful transactions.
        Returns the Bill's paid_amount for USER_MANAGED bills.
        """
        if self.category == BillCategory.USER_MANAGED:
            return self.paid_amount

        from .transaction import Transaction  # Local import to avoid circular dependency
        # Assumes the related_name on Transaction.bill is 'transactions'
        # and Transaction has a 'status' field.
        aggregation = self.transactions.filter(
            status=Transaction.Status.SUCCESSFUL
        ).aggregate(
            total=models.Sum('amount')
        )
        return aggregation['total'] or Decimal('0.00')

    @property
    def is_fully_paid_cluster(self):
        """
        Checks if a CLUSTER_MANAGED bill is fully paid by comparing the
        aggregated transaction amounts to the total bill amount.
        Returns the Bill's is_fully_paid status for USER_MANAGED bills.
        """
        if self.category == BillCategory.USER_MANAGED:
            return self.is_fully_paid

        # The bill is considered paid if the total payments meet or exceed the amount.
        return self.total_paid_amount_cluster >= self.amount

    def get_user_payment_amount(self, user):
        """
        Gets the total amount a specific user has paid towards this bill
        by querying successful transactions linked to their wallet.
        """
        from .transaction import Transaction  # Local import
        # This assumes the Transaction model has a ForeignKey to a Wallet model,
        # which in turn has a ForeignKey to the User model.
        aggregation = self.transactions.filter(
            wallet__user=user,
            status=Transaction.Status.SUCCESSFUL
        ).aggregate(total=models.Sum('amount'))
        return aggregation['total'] or Decimal('0.00')

    def has_user_paid(self, user):
        """
        Checks if a specific user has paid their share of a bill.
        For user-managed bills, checks if the bill is fully paid.
        For cluster-managed bills, checks if the user has paid an amount
        equal to or greater than the bill's total amount.
        """
        if self.category == BillCategory.USER_MANAGED:
            return self.is_fully_paid and str(self.user_id) == str(user.id)

        # For cluster bills, the expected amount for each user is the bill's amount.
        return self.get_user_payment_amount(user) >= self.amount

    def is_user_overdue(self, user):
        """
        Checks if a user is overdue on their portion of a bill.
        A user is overdue if the due date has passed and they have not paid their share.
        This applies even if they haven't acknowledged.
        """
        if self.due_date >= timezone.now():
            return False

        # If due date has passed, they are overdue if they haven't paid their share.
        return not self.has_user_paid(user)


class BillDispute(AbstractClusterModel):
    """
    Model for managing bill disputes.
    
    This model handles disputes for both cluster-wide and user-specific bills,
    allowing multiple users to dispute the same bill with different reasons.
    """

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="disputes",
        verbose_name=_("bill"),
        help_text=_("The bill being disputed"),
    )

    disputed_by = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="bill_disputes",
        verbose_name=_("disputed by"),
        help_text=_("User who raised the dispute"),
    )

    reason = models.TextField(
        verbose_name=_("dispute reason"),
        help_text=_("Detailed reason for disputing the bill"),
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
        help_text=_("Current status of the dispute"),
    )

    admin_notes = models.TextField(
        verbose_name=_("admin notes"),
        blank=True,
        null=True,
        help_text=_("Internal notes from administrators"),
    )

    resolved_by = models.ForeignKey(
        "accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
        verbose_name=_("resolved by"),
        help_text=_("Administrator who resolved the dispute"),
    )

    resolved_at = models.DateTimeField(
        verbose_name=_("resolved at"),
        null=True,
        blank=True,
        help_text=_("Date and time when dispute was resolved"),
    )

    resolution_notes = models.TextField(
        verbose_name=_("resolution notes"),
        blank=True,
        null=True,
        help_text=_("Notes about how the dispute was resolved"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("Bill Dispute")
        verbose_name_plural = _("Bill Disputes")
        indexes = [
            models.Index(fields=["cluster", "bill"]),
            models.Index(fields=["disputed_by"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["resolved_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["bill", "disputed_by"],
                name="unique_bill_dispute_per_user",
                condition=models.Q(status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW])
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute for {self.bill.title} by {self.disputed_by.name}"

    def can_be_disputed_by(self, user):
        """Check if a user can dispute this bill."""
        return self.bill.can_be_acknowledged_by(user)

    def resolve(self, resolved_by, resolution_notes=""):
        """Mark dispute as resolved."""
        self.status = DisputeStatus.RESOLVED
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = resolution_notes
        self.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes"])

    def reject(self, resolved_by, resolution_notes=""):
        """Mark dispute as rejected."""
        self.status = DisputeStatus.REJECTED
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = resolution_notes
        self.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes"])

    def withdraw(self):
        """Allow user to withdraw their dispute."""
        if self.status in [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]:
            self.status = DisputeStatus.WITHDRAWN
            self.resolved_at = timezone.now()
            self.save(update_fields=["status", "resolved_at"])
            return True
        return False

    def set_under_review(self, admin_notes=""):
        """Mark dispute as under review."""
        self.status = DisputeStatus.UNDER_REVIEW
        if admin_notes:
            self.admin_notes = admin_notes
        self.save(update_fields=["status", "admin_notes"])

    @property
    def is_active(self):
        """Check if dispute is still active (not resolved/rejected/withdrawn)."""
        return self.status in [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]

    @property
    def days_since_created(self):
        """Get number of days since dispute was created."""
        return (timezone.now() - self.created_at).days

