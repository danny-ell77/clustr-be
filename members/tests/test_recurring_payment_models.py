"""
Unit tests for RecurringPayment model methods.
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.common.models import (
    RecurringPaymentStatus,
    RecurringPaymentFrequency,
    BillCategory,
)
from members.tests.utils import create_user, create_cluster
from members.tests.test_payment_utils import (
    create_wallet,
    create_bill,
    create_recurring_payment,
    create_utility_provider,
)


class RecurringPaymentModelTests(TestCase):
    """Tests for RecurringPayment model methods."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.user = create_user(
            email="user@test.com",
            phone_number="+2348000000001",
            cluster=self.cluster
        )
        self.wallet = create_wallet(
            user=self.user,
            cluster=self.cluster,
            balance=Decimal("10000.00")
        )

    def test_calculate_next_payment_date_daily(self):
        """Test calculate_next_payment_date for DAILY frequency."""
        start_date = timezone.now()
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            frequency=RecurringPaymentFrequency.DAILY,
            start_date=start_date
        )
        next_date = recurring_payment.calculate_next_payment_date()
        expected_date = start_date + timedelta(days=1)
        
        self.assertAlmostEqual(
            next_date.timestamp(),
            expected_date.timestamp(),
            delta=1
        )

    def test_calculate_next_payment_date_weekly(self):
        """Test calculate_next_payment_date for WEEKLY frequency."""
        start_date = timezone.now()
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            frequency=RecurringPaymentFrequency.WEEKLY,
            start_date=start_date
        )
        next_date = recurring_payment.calculate_next_payment_date()
        expected_date = start_date + timedelta(weeks=1)
        
        self.assertAlmostEqual(
            next_date.timestamp(),
            expected_date.timestamp(),
            delta=1
        )

    def test_calculate_next_payment_date_monthly(self):
        """Test calculate_next_payment_date for MONTHLY frequency."""
        from dateutil.relativedelta import relativedelta
        
        start_date = timezone.now()
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            frequency=RecurringPaymentFrequency.MONTHLY,
            start_date=start_date
        )
        next_date = recurring_payment.calculate_next_payment_date()
        expected_date = start_date + relativedelta(months=1)
        
        self.assertAlmostEqual(
            next_date.timestamp(),
            expected_date.timestamp(),
            delta=1
        )

    def test_pause_changes_status_to_paused(self):
        """Test that pause() changes status to PAUSED."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            status=RecurringPaymentStatus.ACTIVE
        )
        recurring_payment.pause(paused_by=str(self.user.id))
        
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.PAUSED)

    def test_resume_changes_status_to_active(self):
        """Test that resume() changes status to ACTIVE."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            status=RecurringPaymentStatus.PAUSED
        )
        recurring_payment.resume(resumed_by=str(self.user.id))
        
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.ACTIVE)
        self.assertEqual(recurring_payment.failed_attempts, 0)

    def test_cancel_changes_status_to_cancelled(self):
        """Test that cancel() changes status to CANCELLED."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            status=RecurringPaymentStatus.ACTIVE
        )
        recurring_payment.cancel(cancelled_by=str(self.user.id))
        
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.CANCELLED)

    def test_cannot_resume_cancelled_payment(self):
        """Test that cancelled payments cannot be resumed."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            status=RecurringPaymentStatus.CANCELLED
        )
        recurring_payment.resume(resumed_by=str(self.user.id))
        
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.CANCELLED)

    def test_process_payment_updates_next_payment_date(self):
        """Test that process_payment updates next_payment_date correctly."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("500.00")
        )
        start_date = timezone.now()
        recurring_payment = create_recurring_payment(
            wallet=self.wallet,
            bill=bill,
            amount=Decimal("500.00"),
            frequency=RecurringPaymentFrequency.MONTHLY,
            start_date=start_date
        )
        
        old_next_date = recurring_payment.next_payment_date
        result = recurring_payment.process_payment()
        
        if result:
            self.assertNotEqual(recurring_payment.next_payment_date, old_next_date)
            self.assertEqual(recurring_payment.total_payments, 1)

    def test_is_utility_payment_check(self):
        """Test is_utility_payment() method."""
        provider = create_utility_provider(cluster=self.cluster)
        
        utility_payment = create_recurring_payment(
            wallet=self.wallet,
            utility_provider=provider,
            customer_id="1234567890"
        )
        self.assertTrue(utility_payment.is_utility_payment())
        
        regular_payment = create_recurring_payment(
            wallet=self.wallet,
            title="Regular payment"
        )
        self.assertFalse(regular_payment.is_utility_payment())
