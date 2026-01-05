"""
Unit tests for Bill model methods.
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.common.models import (
    Bill,
    BillType,
    BillStatus,
    BillCategory,
    BillDispute,
)
from members.tests.utils import create_user, create_cluster
from members.tests.test_payment_utils import create_bill, create_wallet


class BillModelTests(TestCase):
    """Tests for Bill model methods."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.user1 = create_user(
            email="user1@test.com",
            phone_number="+2348000000001",
            cluster=self.cluster
        )
        self.user2 = create_user(
            email="user2@test.com",
            phone_number="+2348000000002",
            cluster=self.cluster
        )

    def test_bill_creation_generates_bill_number(self):
        """Test that bill creation automatically generates a bill number."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED
        )
        self.assertIsNotNone(bill.bill_number)
        self.assertTrue(bill.bill_number.startswith("BILL-"))

    def test_is_cluster_wide_returns_true_for_null_user(self):
        """Test is_cluster_wide property for cluster-managed bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=None,
            category=BillCategory.CLUSTER_MANAGED
        )
        self.assertTrue(bill.is_cluster_wide)

    def test_is_cluster_wide_returns_false_for_specific_user(self):
        """Test is_cluster_wide property for user-managed bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED
        )
        self.assertFalse(bill.is_cluster_wide)

    def test_can_be_acknowledged_by_cluster_member(self):
        """Test that cluster-managed bills can be acknowledged by any member."""
        bill = create_bill(
            cluster=self.cluster,
            user=None,
            category=BillCategory.CLUSTER_MANAGED,
            status=BillStatus.PENDING
        )
        self.assertTrue(bill.acknowledge())
        self.assertIn(self.admin, bill.acknowledged_by.all())

    def test_can_be_acknowledged_by_target_user_only(self):
        """Test that user-managed bills can only be acknowledged by assigned user."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        result = bill.acknowledge(user_id=str(self.user1.id))
        self.assertTrue(result)
        self.assertIn(self.user1, bill.acknowledged_by.all())
        self.assertEqual(bill.status, BillStatus.ACKNOWLEDGED)

    def test_acknowledge_adds_user_to_acknowledged_by(self):
        """Test that acknowledging a bill adds user to acknowledged_by list."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        bill.acknowledge(user_id=str(self.user1.id))
        self.assertEqual(bill.acknowledged_by.count(), 1)
        self.assertIn(self.user1, bill.acknowledged_by.all())

    def test_acknowledge_returns_false_if_already_acknowledged(self):
        """Test that acknowledging an already acknowledged bill returns False."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        bill.acknowledge(user_id=str(self.user1.id))
        result = bill.acknowledge(user_id=str(self.user1.id))
        self.assertFalse(result)

    def test_can_be_paid_by_requires_acknowledgment_for_user_managed(self):
        """Test that user-managed bills require acknowledgment before payment."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        self.assertFalse(bill.can_be_paid_by(self.user1))
        
        bill.acknowledge(user_id=str(self.user1.id))
        bill.refresh_from_db()
        self.assertTrue(bill.can_be_paid_by(self.user1))

    def test_can_be_paid_by_respects_due_date_restrictions(self):
        """Test that bills respect due date payment restrictions."""
        past_due_date = timezone.now() - timedelta(days=1)
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED,
            due_date=past_due_date
        )
        bill.allow_payment_after_due = False
        bill.save()
        
        self.assertFalse(bill.can_be_paid_by(self.user1))
        
        bill.allow_payment_after_due = True
        bill.save()
        self.assertTrue(bill.can_be_paid_by(self.user1))

    def test_is_overdue_for_unpaid_past_due_bill(self):
        """Test is_overdue property for unpaid bills past due date."""
        past_due_date = timezone.now() - timedelta(days=1)
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            due_date=past_due_date,
            status=BillStatus.ACKNOWLEDGED
        )
        self.assertTrue(bill.is_overdue)

    def test_is_not_overdue_when_paid(self):
        """Test is_overdue property for paid bills."""
        past_due_date = timezone.now() - timedelta(days=1)
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            due_date=past_due_date,
            status=BillStatus.PAID
        )
        self.assertFalse(bill.is_overdue)

    def test_is_fully_paid_when_paid_amount_equals_total(self):
        """Test is_fully_paid property when amount is fully paid."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("1000.00")
        )
        bill.paid_amount = Decimal("1000.00")
        bill.save()
        self.assertTrue(bill.is_fully_paid)

    def test_is_partially_paid_when_partial_payment(self):
        """Test partial payment status."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("1000.00")
        )
        bill.paid_amount = Decimal("500.00")
        bill.save()
        self.assertFalse(bill.is_fully_paid)
        self.assertGreater(bill.paid_amount, Decimal("0"))

    def test_remaining_amount_calculation(self):
        """Test remaining_amount property calculation."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("1000.00")
        )
        bill.paid_amount = Decimal("400.00")
        bill.save()
        self.assertEqual(bill.remaining_amount, Decimal("600.00"))

    def test_dispute_creates_dispute_record(self):
        """Test that disputing a bill creates a BillDispute record."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        reason = "Amount is incorrect"
        result = bill.dispute(user_id=str(self.user1.id), reason=reason)
        
        self.assertIsInstance(result, BillDispute)
        self.assertEqual(result.reason, reason)
        self.assertEqual(bill.status, BillStatus.DISPUTED)

    def test_dispute_returns_existing_active_dispute(self):
        """Test that disputing an already disputed bill returns existing dispute."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        dispute1 = bill.dispute(user_id=str(self.user1.id), reason="First dispute")
        dispute2 = bill.dispute(user_id=str(self.user1.id), reason="Second dispute")
        
        self.assertEqual(dispute1.id, dispute2.id)

    def test_dispute_not_allowed_when_fully_paid(self):
        """Test that fully paid bills cannot be disputed."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PAID,
            amount=Decimal("1000.00")
        )
        bill.paid_amount = Decimal("1000.00")
        bill.save()
        
        result = bill.dispute(user_id=str(self.user1.id), reason="Disputing paid bill")
        self.assertIsNone(result)

    def test_mark_as_paid_sets_correct_fields(self):
        """Test that mark_as_paid sets status and paid_by correctly."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        bill.mark_as_paid(paid_by=str(self.user1.id))
        
        self.assertEqual(bill.status, BillStatus.PAID)
        self.assertEqual(bill.paid_by, str(self.user1.id))
        self.assertIsNotNone(bill.paid_at)

    def test_mark_as_paid_only_for_user_managed_bills(self):
        """Test that mark_as_paid is primarily for USER_MANAGED bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED,
            amount=Decimal("1000.00")
        )
        bill.mark_as_paid(paid_by=str(self.user1.id))
        
        self.assertEqual(bill.status, BillStatus.PAID)
        self.assertEqual(bill.paid_amount, bill.amount)

    def test_can_be_paid_returns_false_when_disputed(self):
        """Test that disputed bills cannot be paid."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        bill.dispute(user_id=str(self.user1.id), reason="Incorrect amount")
        bill.refresh_from_db()
        
        self.assertFalse(bill.can_be_paid())
