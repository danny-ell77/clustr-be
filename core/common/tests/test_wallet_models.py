"""
Tests for wallet models and utilities.
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from core.common.models import (
    Cluster,
    Wallet,
    Transaction,
    Bill,
    RecurringPayment,
    WalletStatus,
    TransactionType,
    TransactionStatus,
    BillStatus,
    BillType,
    RecurringPaymentStatus,
    RecurringPaymentFrequency,
    PaymentProvider,
)
from core.common.includes import bills, cluster_wallet, payments, recurring_payments


class WalletModelTest(TestCase):
    """Test wallet model functionality."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

        self.wallet = Wallet.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
            currency="NGN",
            status=WalletStatus.ACTIVE,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

    def test_wallet_creation(self):
        """Test wallet creation."""
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("1000.00"))
        self.assertEqual(self.wallet.currency, "NGN")
        self.assertEqual(self.wallet.status, WalletStatus.ACTIVE)

    def test_wallet_balance_update(self):
        """Test wallet balance update."""
        # Test deposit
        self.wallet.update_balance(Decimal("500.00"), TransactionType.DEPOSIT)
        self.assertEqual(self.wallet.balance, Decimal("1500.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("1500.00"))

        # Test withdrawal
        self.wallet.update_balance(Decimal("200.00"), TransactionType.WITHDRAWAL)
        self.assertEqual(self.wallet.balance, Decimal("1300.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("1300.00"))

    def test_wallet_sufficient_balance_check(self):
        """Test wallet sufficient balance check."""
        self.assertTrue(self.wallet.has_sufficient_balance(Decimal("500.00")))
        self.assertTrue(self.wallet.has_sufficient_balance(Decimal("1000.00")))
        self.assertFalse(self.wallet.has_sufficient_balance(Decimal("1500.00")))

    def test_wallet_freeze_unfreeze_amount(self):
        """Test wallet freeze and unfreeze functionality."""
        # Test freeze
        self.assertTrue(self.wallet.freeze_amount(Decimal("300.00")))
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("700.00"))

        # Test unfreeze
        self.wallet.unfreeze_amount(Decimal("100.00"))
        self.assertEqual(self.wallet.balance, Decimal("1000.00"))
        self.assertEqual(self.wallet.available_balance, Decimal("800.00"))

        # Test freeze insufficient balance
        self.assertFalse(self.wallet.freeze_amount(Decimal("900.00")))


class TransactionModelTest(TestCase):
    """Test transaction model functionality."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

        self.wallet = Wallet.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
            currency="NGN",
            status=WalletStatus.ACTIVE,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

    def test_transaction_creation(self):
        """Test transaction creation."""
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self.wallet,
            type=TransactionType.DEPOSIT,
            amount=Decimal("500.00"),
            currency="NGN",
            description="Test deposit",
            provider=PaymentProvider.PAYSTACK,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        self.assertIsNotNone(transaction.transaction_id)
        self.assertTrue(transaction.transaction_id.startswith("TXN-"))
        self.assertEqual(transaction.status, TransactionStatus.PENDING)

    def test_transaction_completion(self):
        """Test transaction completion."""
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self.wallet,
            type=TransactionType.DEPOSIT,
            amount=Decimal("500.00"),
            currency="NGN",
            description="Test deposit",
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        original_balance = self.wallet.balance
        transaction.mark_as_completed()

        self.assertEqual(transaction.status, TransactionStatus.COMPLETED)
        self.assertIsNotNone(transaction.processed_at)

        # Refresh wallet from database
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, original_balance + Decimal("500.00"))

    def test_transaction_failure(self):
        """Test transaction failure."""
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self.wallet,
            type=TransactionType.WITHDRAWAL,
            amount=Decimal("200.00"),
            currency="NGN",
            description="Test withdrawal",
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        # Freeze amount first
        self.wallet.freeze_amount(Decimal("200.00"))

        transaction.mark_as_failed("Test failure reason")

        self.assertEqual(transaction.status, TransactionStatus.FAILED)
        self.assertIsNotNone(transaction.failed_at)
        self.assertEqual(transaction.failure_reason, "Test failure reason")

        # Check that amount was unfrozen
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("1000.00"))


class BillModelTest(TestCase):
    """Test bill model functionality."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

    def test_bill_creation(self):
        """Test bill creation."""
        due_date = timezone.now() + timezone.timedelta(days=30)

        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            title="Test Bill",
            description="Test bill description",
            type=BillType.ELECTRICITY,
            amount=Decimal("5000.00"),
            due_date=due_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        self.assertIsNotNone(bill.bill_number)
        self.assertTrue(bill.bill_number.startswith("BILL-"))
        self.assertEqual(bill.status, BillStatus.PENDING)
        self.assertEqual(bill.remaining_amount, Decimal("5000.00"))

    def test_bill_payment(self):
        """Test bill payment."""
        due_date = timezone.now() + timezone.timedelta(days=30)

        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            title="Test Bill",
            type=BillType.ELECTRICITY,
            amount=Decimal("5000.00"),
            due_date=due_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        # Test partial payment
        bill.add_payment(Decimal("2000.00"))
        self.assertEqual(bill.paid_amount, Decimal("2000.00"))
        self.assertEqual(bill.remaining_amount, Decimal("3000.00"))
        self.assertEqual(bill.status, BillStatus.PARTIALLY_PAID)

        # Test full payment
        bill.add_payment(Decimal("3000.00"))
        self.assertEqual(bill.paid_amount, Decimal("5000.00"))
        self.assertEqual(bill.remaining_amount, Decimal("0.00"))
        self.assertEqual(bill.status, BillStatus.PAID)
        self.assertIsNotNone(bill.paid_at)

        # Test that cluster wallet was credited
        wallet = Wallet.objects.filter(
            cluster=self.cluster,
            user_id=self.cluster.id,
        ).first()

        # Cluster wallet should be created and credited with bill payments
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.balance, Decimal("5000.00"))  # 2000 + 3000

    def test_bill_overdue_check(self):
        """Test bill overdue check."""
        # Create overdue bill
        overdue_date = timezone.now() - timezone.timedelta(days=5)

        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            title="Overdue Bill",
            type=BillType.ELECTRICITY,
            amount=Decimal("5000.00"),
            due_date=overdue_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        self.assertTrue(bill.is_overdue)

        # Mark as paid and check again
        bill.mark_as_paid()
        self.assertFalse(bill.is_overdue)


class RecurringPaymentModelTest(TestCase):
    """Test recurring payment model functionality."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

        self.wallet = Wallet.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            balance=Decimal("10000.00"),
            available_balance=Decimal("10000.00"),
            currency="NGN",
            status=WalletStatus.ACTIVE,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

    def test_recurring_payment_creation(self):
        """Test recurring payment creation."""
        start_date = timezone.now() + timezone.timedelta(days=1)

        payment = RecurringPayment.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            wallet=self.wallet,
            title="Monthly Service Charge",
            amount=Decimal("2000.00"),
            frequency=RecurringPaymentFrequency.MONTHLY,
            start_date=start_date,
            next_payment_date=start_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        self.assertEqual(payment.status, RecurringPaymentStatus.ACTIVE)
        self.assertEqual(payment.total_payments, 0)
        self.assertEqual(payment.failed_attempts, 0)

    def test_recurring_payment_processing(self):
        """Test recurring payment processing."""
        start_date = timezone.now()

        payment = RecurringPayment.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            wallet=self.wallet,
            title="Monthly Service Charge",
            amount=Decimal("2000.00"),
            frequency=RecurringPaymentFrequency.MONTHLY,
            start_date=start_date,
            next_payment_date=start_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        original_balance = self.wallet.balance

        # Process payment
        result = payment.process_payment()

        self.assertTrue(result)
        self.assertEqual(payment.total_payments, 1)
        self.assertEqual(payment.failed_attempts, 0)
        self.assertIsNotNone(payment.last_payment_date)

        # Check wallet balance
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, original_balance - Decimal("2000.00"))

    def test_recurring_payment_insufficient_funds(self):
        """Test recurring payment with insufficient funds."""
        # Set low wallet balance
        self.wallet.balance = Decimal("100.00")
        self.wallet.available_balance = Decimal("100.00")
        self.wallet.save()

        start_date = timezone.now()

        payment = RecurringPayment.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            wallet=self.wallet,
            title="Monthly Service Charge",
            amount=Decimal("2000.00"),
            frequency=RecurringPaymentFrequency.MONTHLY,
            start_date=start_date,
            next_payment_date=start_date,
            max_failed_attempts=2,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        # Process payment (should fail)
        result = payment.process_payment()

        self.assertFalse(result)
        self.assertEqual(payment.total_payments, 0)
        self.assertEqual(payment.failed_attempts, 1)
        self.assertEqual(payment.status, RecurringPaymentStatus.ACTIVE)

        # Process again (should pause after max attempts)
        result = payment.process_payment()

        self.assertFalse(result)
        self.assertEqual(payment.failed_attempts, 2)
        self.assertEqual(payment.status, RecurringPaymentStatus.PAUSED)


class PaymentUtilsTest(TestCase):
    """Test payment utilities."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

        self.wallet = Wallet.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            balance=Decimal("10000.00"),
            available_balance=Decimal("10000.00"),
            currency="NGN",
            status=WalletStatus.ACTIVE,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

    @patch("core.common.utils.payment_utils.PaymentManager.get_processor")
    def test_payment_manager_initialization(self, mock_get_processor):
        """Test payment manager initialization."""

        # Test getting Paystack processor
        mock_processor = MagicMock()
        mock_get_processor.return_value = mock_processor

        processor = payments.get_processor(PaymentProvider.PAYSTACK)
        self.assertEqual(processor, mock_processor)

    def test_bill_manager_creation(self):
        """Test bill manager bill creation."""
        due_date = timezone.now() + timezone.timedelta(days=30)

        with patch(
            "core.common.utils.bill_utils.BillNotificationManager.send_new_bill_notification"
        ) as mock_notify:
            mock_notify.return_value = True

            bill = bills.create(
                cluster=self.cluster,
                user_id=str(self.user_id),
                title="Test Utility Bill",
                amount=Decimal("3000.00"),
                bill_type=BillType.ELECTRICITY,
                due_date=due_date,
                description="Monthly electricity bill",
                created_by=str(self.user_id),
            )

            self.assertIsNotNone(bill)
            self.assertEqual(bill.title, "Test Utility Bill")
            self.assertEqual(bill.amount, Decimal("3000.00"))
            self.assertEqual(bill.type, BillType.ELECTRICITY)
            mock_notify.assert_called_once_with(bill)

    def test_recurring_payment_manager_creation(self):
        """Test recurring payment manager creation."""
        start_date = timezone.now() + timezone.timedelta(days=1)

        with patch(
            "core.common.utils.recurring_payment_utils.RecurringPaymentNotificationManager.send_setup_confirmation"
        ) as mock_notify:
            mock_notify.return_value = True

            payment = recurring_payments.create(
                wallet=self.wallet,
                title="Test Recurring Payment",
                amount=Decimal("1500.00"),
                frequency=RecurringPaymentFrequency.MONTHLY,
                start_date=start_date,
                description="Test recurring payment",
                created_by=str(self.user_id),
            )

            self.assertIsNotNone(payment)
            self.assertEqual(payment.title, "Test Recurring Payment")
            self.assertEqual(payment.amount, Decimal("1500.00"))
            self.assertEqual(payment.frequency, RecurringPaymentFrequency.MONTHLY)
            mock_notify.assert_called_once_with(payment)

    def test_payment_error_handler_categorization(self):
        """Test payment error handler error categorization."""
        from core.common.includes import payment_error

        # Test insufficient funds error
        error_type = payments.categorize_error(
            "Insufficient funds in account", PaymentProvider.PAYSTACK
        )
        self.assertEqual(error_type, payment_error.PaymentErrorType.INSUFFICIENT_FUNDS)

        # Test invalid card error
        error_type = payments.categorize_error(
            "Invalid card number provided", PaymentProvider.PAYSTACK
        )
        self.assertEqual(error_type, payment_error.PaymentErrorType.INVALID_CARD)

        # Test network error
        error_type = payments.categorize_error(
            "Network timeout occurred", PaymentProvider.FLUTTERWAVE
        )
        self.assertEqual(error_type, payment_error.PaymentErrorType.NETWORK_ERROR)

    def test_payment_error_recovery_options(self):
        """Test payment error recovery options."""
        transaction = Transaction.objects.create(
            cluster=self.cluster,
            wallet=self.wallet,
            type=TransactionType.PAYMENT,
            amount=Decimal("500.00"),
            currency="NGN",
            description="Test payment",
            provider=PaymentProvider.PAYSTACK,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        from core.common.includes import payment_error

        # Test insufficient funds recovery options
        options = payment_error.get_recovery_options(
            payment_error.PaymentErrorType.INSUFFICIENT_FUNDS, transaction
        )

        self.assertFalse(options["can_retry"])
        self.assertIn("bank_transfer", options["alternative_methods"])
        self.assertIn("Add funds to your wallet", options["suggested_actions"])

        # Test network error recovery options
        options = payment_error.get_recovery_options(
            payment_error.PaymentErrorType.NETWORK_ERROR, transaction
        )

        self.assertTrue(options["can_retry"])
        self.assertEqual(options["max_retries"], 5)
        self.assertEqual(options["retry_delay_minutes"], 2)


class ClusterWalletTest(TestCase):
    """Test cluster wallet functionality."""

    def setUp(self):
        """Set up test data."""
        self.cluster = Cluster.objects.create(
            name="Test Estate",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Nigeria",
        )

        self.user_id = uuid.uuid4()

    def test_cluster_wallet_creation(self):
        """Test cluster wallet creation."""

        wallet = cluster_wallet.get_or_create_cluster_wallet(
            self.cluster, str(self.user_id)
        )

        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.balance, Decimal("0.00"))
        self.assertEqual(wallet.available_balance, Decimal("0.00"))
        self.assertEqual(wallet.currency, "NGN")
        self.assertEqual(wallet.status, WalletStatus.ACTIVE)

    def test_cluster_wallet_bill_payment_credit(self):
        """Test that bill payments credit the cluster wallet."""
        # Create a bill
        due_date = timezone.now() + timezone.timedelta(days=30)

        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user_id,
            title="Test Bill",
            type=BillType.ELECTRICITY,
            amount=Decimal("1000.00"),
            due_date=due_date,
            created_by=self.user_id,
            last_modified_by=self.user_id,
        )

        # Pay the bill
        bill.add_payment(Decimal("1000.00"))

        # Check that cluster wallet was credited

        cluster_wallet = Wallet.objects.get(
            cluster=self.cluster, user_id=self.cluster.id
        )

        self.assertEqual(cluster_wallet.balance, Decimal("1000.00"))

        # Check that a credit transaction was created
        credit_transaction = Transaction.objects.filter(
            wallet=cluster_wallet,
            type=TransactionType.DEPOSIT,
            amount=Decimal("1000.00"),
        ).first()

        self.assertIsNotNone(credit_transaction)
        self.assertEqual(credit_transaction.status, TransactionStatus.COMPLETED)
        self.assertIn("bill_payment", credit_transaction.metadata["source"])

    def test_cluster_wallet_analytics(self):
        """Test cluster wallet analytics."""

        # Create and pay some bills
        for i in range(3):
            due_date = timezone.now() + timezone.timedelta(days=30)

            bill = Bill.objects.create(
                cluster=self.cluster,
                user_id=self.user_id,
                title=f"Test Bill {i+1}",
                type=BillType.ELECTRICITY,
                amount=Decimal("500.00"),
                due_date=due_date,
                created_by=self.user_id,
                last_modified_by=self.user_id,
            )

            bill.add_payment(Decimal("500.00"))

        # Get analytics
        analytics = cluster_wallet.get_cluster_wallet_analytics(self.cluster)

        self.assertEqual(analytics["current_balance"], Decimal("1500.00"))
        self.assertEqual(analytics["total_deposits"], Decimal("1500.00"))
        self.assertEqual(analytics["total_withdrawals"], Decimal("0.00"))
        self.assertEqual(analytics["bill_payment_revenue"], Decimal("1500.00"))
        self.assertEqual(analytics["bill_payment_count"], 3)

    def test_cluster_wallet_transfer(self):
        """Test cluster wallet transfer functionality."""

        # First, add some funds to cluster wallet
        cluster_wallet.add_manual_credit(
            cluster=self.cluster,
            amount=Decimal("5000.00"),
            description="Initial funding",
            added_by=str(self.user_id),
        )

        # Now transfer some funds
        transaction = cluster_wallet.transfer_from_cluster_wallet(
            cluster=self.cluster,
            amount=Decimal("2000.00"),
            description="Transfer to bank account",
            recipient_account="1234567890",
            transferred_by=str(self.user_id),
        )

        self.assertEqual(transaction.type, TransactionType.WITHDRAWAL)
        self.assertEqual(transaction.amount, Decimal("2000.00"))
        self.assertEqual(transaction.status, TransactionStatus.COMPLETED)

        # Check remaining balance
        balance_info = cluster_wallet.get_cluster_wallet_balance(self.cluster)
        self.assertEqual(balance_info["balance"], Decimal("3000.00"))

    def test_cluster_wallet_insufficient_funds_transfer(self):
        """Test cluster wallet transfer with insufficient funds."""

        # Try to transfer without sufficient funds
        with self.assertRaises(ValueError) as context:
            cluster_wallet.transfer_from_cluster_wallet(
                cluster=self.cluster,
                amount=Decimal("1000.00"),
                description="Transfer attempt",
                transferred_by=str(self.user_id),
            )

        self.assertIn("Insufficient cluster wallet balance", str(context.exception))
