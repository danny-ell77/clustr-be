"""
Wallet models for ClustR application.
"""

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

