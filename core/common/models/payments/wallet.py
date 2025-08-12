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
        default_permissions = []
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        unique_together = [["user_id", "cluster"]]
        indexes = [
            models.Index(fields=["user_id", "cluster"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Wallet for User {self.user_id} - {self.currency} {self.balance}"

    def update_balance(self, amount, transaction_type, description="Balance update"):
        """
        Update wallet balance based on transaction type.
        
        DEPRECATED: Use debit() or credit() methods instead for cleaner code.

        Args:
            amount: Amount to add/subtract
            transaction_type: Type of transaction (deposit, withdrawal, etc.)
            description: Description for logging
        """
        from .transaction import TransactionType
        
        logger.warning("update_balance() is deprecated. Use debit() or credit() methods instead.")
        
        if transaction_type in [TransactionType.DEPOSIT, TransactionType.REFUND]:
            return self.credit(amount, description)
        elif transaction_type in [
            TransactionType.WITHDRAWAL,
            TransactionType.PAYMENT,
            TransactionType.BILL_PAYMENT,
        ]:
            return self.debit(amount, description)
        else:
            # Fallback for unknown transaction types - direct balance update
            if transaction_type in [TransactionType.DEPOSIT, TransactionType.REFUND]:
                self.balance += amount
                self.available_balance += amount
            else:
                self.balance -= amount
                self.available_balance -= amount
            
            self.last_transaction_at = timezone.now()
            self.save(update_fields=["balance", "available_balance", "last_transaction_at"])
            return True

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

    def debit(self, amount, description="Balance debit"):
        """
        Atomic debit operation - removes money from wallet.
        
        Args:
            amount: Amount to debit
            description: Description for logging (optional)
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If insufficient balance or invalid amount
        """
        if amount <= 0:
            raise ValueError("Debit amount must be greater than 0")
            
        if not self.has_sufficient_balance(amount):
            raise ValueError(f"Insufficient balance. Available: {self.available_balance}, Required: {amount}")
        
        # Update wallet balances only
        self.balance -= amount
        self.available_balance -= amount
        self.last_transaction_at = timezone.now()
        self.save(update_fields=["balance", "available_balance", "last_transaction_at"])
        
        logger.info(f"Wallet debited: {amount} {self.currency} - {description}")
        return True

    def credit(self, amount, description="Balance credit"):
        """
        Atomic credit operation - adds money to wallet.
        
        Args:
            amount: Amount to credit
            description: Description for logging (optional)
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If invalid amount
        """
        if amount <= 0:
            raise ValueError("Credit amount must be greater than 0")
        
        # Update wallet balances only
        self.balance += amount
        self.available_balance += amount
        self.last_transaction_at = timezone.now()
        self.save(update_fields=["balance", "available_balance", "last_transaction_at"])
        
        logger.info(f"Wallet credited: {amount} {self.currency} - {description}")
        return True

    def get_transaction_history(self, limit=50, transaction_type=None):
        """
        Get wallet transaction history.
        
        Args:
            limit: Maximum number of transactions to return
            transaction_type: Filter by transaction type (optional)
            
        Returns:
            QuerySet: Transaction objects ordered by creation date (newest first)
        """
        transactions = self.transactions.all()
        
        if transaction_type:
            transactions = transactions.filter(type=transaction_type)
            
        return transactions.order_by('-created_at')[:limit]

    def get_balance_summary(self):
        """
        Get comprehensive balance summary.
        
        Returns:
            dict: Balance summary with totals and recent activity
        """
        from .transaction import TransactionType
        
        # Calculate totals by transaction type
        recent_transactions = self.get_transaction_history(limit=10)
        
        return {
            'current_balance': self.balance,
            'available_balance': self.available_balance,
            'frozen_amount': self.balance - self.available_balance,
            'currency': self.currency,
            'last_transaction_at': self.last_transaction_at,
            'recent_transactions': [
                {
                    'id': t.transaction_id,
                    'type': t.type,
                    'amount': t.amount,
                    'description': t.description,
                    'status': t.status,
                    'created_at': t.created_at,
                }
                for t in recent_transactions
            ]
        }    

    def create_pending_transaction(self, amount, description, transaction_type, freeze_amount=True):
        """
        Create a pending transaction without updating wallet balance.
        Use this for transactions that will be completed later via webhooks or external confirmation.
        
        Args:
            amount: Transaction amount
            description: Transaction description
            transaction_type: Type of transaction
            freeze_amount: Whether to freeze the amount for withdrawals (default: True)
            
        Returns:
            Transaction: Created pending transaction
            
        Raises:
            ValueError: If insufficient balance for withdrawals
        """
        from .transaction import Transaction, TransactionType, TransactionStatus
        
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than 0")
        
        # For withdrawal-type transactions, check balance and optionally freeze amount
        if transaction_type in [TransactionType.WITHDRAWAL, TransactionType.PAYMENT, TransactionType.BILL_PAYMENT]:
            if not self.has_sufficient_balance(amount):
                raise ValueError(f"Insufficient balance. Available: {self.available_balance}, Required: {amount}")
            
            if freeze_amount:
                if not self.freeze_amount(amount):
                    raise ValueError("Failed to freeze amount for pending transaction")
        
        # Create pending transaction (balance will be updated when marked as completed)
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self,
            type=transaction_type,
            amount=amount,
            currency=self.currency,
            description=description,
            status=TransactionStatus.PENDING,
        )
        
        logger.info(f"Pending transaction created: {transaction.transaction_id} - {description}")
        return transaction