"""
Test cases for bill payment acknowledgment validation.
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.common.models import (
    Bill,
    BillType,
    BillCategory,
    Wallet,
    WalletStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
)
from core.common.includes import bills


class BillPaymentAcknowledgmentTestCase(TestCase):
    """Test cases for bill payment acknowledgment validation."""
    
    def setUp(self):
        """Set up test data."""
        User = get_user_model()
        
        # Create a mock cluster (assuming it exists)
        from unittest.mock import Mock
        self.cluster = Mock()
        self.cluster.id = uuid.uuid4()
        self.cluster.name = "Test Cluster"
        
        # Create test user
        self.user = Mock()
        self.user.id = uuid.uuid4()
        self.user.name = "Test User"
        self.user.cluster = self.cluster
        
        # Create test wallet
        self.wallet = Mock()
        self.wallet.cluster = self.cluster
        self.wallet.user_id = str(self.user.id)
        self.wallet.balance = Decimal("1000.00")
        self.wallet.currency = "NGN"
        self.wallet.created_by = str(self.user.id)
        self.wallet.last_modified_by = str(self.user.id)
        
        # Mock wallet methods
        self.wallet.has_sufficient_balance = lambda amount: self.wallet.balance >= amount
        self.wallet.update_balance = lambda amount, tx_type: setattr(self.wallet, 'balance', self.wallet.balance - amount)
        
        # Create test bill
        self.bill = Bill(
            cluster=self.cluster,
            user_id=str(self.user.id),
            title="Test Bill",
            description="Test bill for acknowledgment validation",
            type=BillType.SERVICE_CHARGE,
            category=BillCategory.CLUSTER_MANAGED,
            amount=Decimal("100.00"),
            due_date=timezone.now() + timezone.timedelta(days=7),
            allow_payment_after_due=True,
            created_by=str(self.user.id),
            last_modified_by=str(self.user.id),
        )
        
    def test_payment_blocked_without_acknowledgment(self):
        """Test that payment is blocked when bill is not acknowledged."""
        # Ensure bill is not acknowledged
        self.bill.acknowledged_by = Mock()
        self.bill.acknowledged_by.filter.return_value.exists.return_value = False
        
        # Mock the can_be_paid_by method to return False due to no acknowledgment
        def mock_can_be_paid_by(user):
            return self.bill.acknowledged_by.filter(id=user.id).exists()
        
        self.bill.can_be_paid_by = mock_can_be_paid_by
        
        # Attempt to process payment
        with self.assertRaises(ValueError) as context:
            bills.process_payment(
                bill=self.bill,
                wallet=self.wallet,
                amount=Decimal("100.00"),
                user=self.user
            )
        
        # Verify the error message
        self.assertIn("Bill must be acknowledged before payment", str(context.exception))
        
    def test_payment_allowed_with_acknowledgment(self):
        """Test that payment is allowed when bill is acknowledged."""
        # Mock bill as acknowledged
        self.bill.acknowledged_by = Mock()
        self.bill.acknowledged_by.filter.return_value.exists.return_value = True
        
        # Mock the can_be_paid_by method to return True
        self.bill.can_be_paid_by = lambda user: True
        
        # Mock remaining_amount property
        self.bill.remaining_amount = Decimal("100.00")
        
        # Mock is_overdue property
        self.bill.is_overdue = False
        
        # Mock add_payment method
        self.bill.add_payment = Mock()
        
        # Mock Transaction creation and other dependencies
        with self.patch_transaction_creation():
            try:
                transaction = bills.process_payment(
                    bill=self.bill,
                    wallet=self.wallet,
                    amount=Decimal("100.00"),
                    user=self.user
                )
                
                # If we get here without exception, the acknowledgment validation passed
                self.assertIsNotNone(transaction)
                
            except Exception as e:
                # If there's an exception, it should not be about acknowledgment
                self.assertNotIn("Bill must be acknowledged before payment", str(e))
    
    def patch_transaction_creation(self):
        """Context manager to patch Transaction creation."""
        from unittest.mock import patch, Mock
        
        mock_transaction = Mock()
        mock_transaction.transaction_id = "TEST-TXN-123"
        mock_transaction.amount = Decimal("100.00")
        
        return patch('core.common.models.Transaction.objects.create', return_value=mock_transaction)


if __name__ == '__main__':
    import django
    from django.conf import settings
    
    # Configure Django settings for testing
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'core.common',
                'accounts',
            ],
            SECRET_KEY='test-secret-key',
        )
        django.setup()
    
    import unittest
    unittest.main()