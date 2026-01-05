"""
Unit tests for BillDispute model methods.
"""
from django.test import TestCase
from django.db import IntegrityError

from core.common.models import (
    BillStatus,
    BillCategory,
    DisputeStatus,
)
from members.tests.utils import create_user, create_cluster
from members.tests.test_payment_utils import create_bill, create_bill_dispute


class BillDisputeModelTests(TestCase):
    """Tests for BillDispute model methods."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.user = create_user(
            email="user@test.com",
            phone_number="+2348000000001",
            cluster=self.cluster
        )
        self.bill = create_bill(
            cluster=self.cluster,
            user=self.user,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )

    def test_dispute_creation_with_open_status(self):
        """Test that new disputes are created with OPEN status."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            reason="Incorrect amount"
        )
        self.assertEqual(dispute.status, DisputeStatus.OPEN)
        self.assertEqual(dispute.bill, self.bill)
        self.assertEqual(dispute.user_id, self.user.id)

    def test_resolve_sets_correct_status_and_fields(self):
        """Test that resolve() sets status to RESOLVED with correct fields."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user
        )
        resolution = "Bill amount was verified and is correct"
        dispute.resolve(resolved_by=str(self.admin.id), resolution=resolution)
        
        self.assertEqual(dispute.status, BillDisputeStatus.RESOLVED)
        self.assertEqual(dispute.resolution, resolution)
        self.assertEqual(dispute.resolved_by, str(self.admin.id))
        self.assertIsNotNone(dispute.resolved_at)

    def test_reject_sets_correct_status_and_fields(self):
        """Test that reject() sets status to REJECTED with correct fields."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user
        )
        resolution = "Dispute is not valid"
        dispute.reject(rejected_by=str(self.admin.id), resolution=resolution)
        
        self.assertEqual(dispute.status, DisputeStatus.REJECTED)
        self.assertEqual(dispute.resolution, resolution)
        self.assertEqual(dispute.resolved_by, str(self.admin.id))
        self.assertIsNotNone(dispute.resolved_at)

    def test_withdraw_allowed_when_open_or_under_review(self):
        """Test that disputes can be withdrawn when OPEN or UNDER_REVIEW."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=DisputeStatus.OPEN
        )
        result = dispute.withdraw(withdrawn_by=str(self.user.id))
        
        self.assertTrue(result)
        self.assertEqual(dispute.status, DisputeStatus.WITHDRAWN)
        
        dispute2 = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=DisputeStatus.UNDER_REVIEW,
            reason="Another dispute"
        )
        result2 = dispute2.withdraw(withdrawn_by=str(self.user.id))
        self.assertTrue(result2)

    def test_withdraw_not_allowed_when_resolved(self):
        """Test that resolved disputes cannot be withdrawn."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.RESOLVED
        )
        result = dispute.withdraw(withdrawn_by=str(self.user.id))
        
        self.assertFalse(result)
        self.assertEqual(dispute.status, BillDisputeStatus.RESOLVED)

    def test_set_under_review_changes_status(self):
        """Test that set_under_review() changes status to UNDER_REVIEW."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.OPEN
        )
        dispute.set_under_review(reviewed_by=str(self.admin.id))
        
        self.assertEqual(dispute.status, DisputeStatus.UNDER_REVIEW)
        self.assertIsNotNone(dispute.last_modified_by)

    def test_is_active_for_open_disputes(self):
        """Test that is_active returns True for OPEN disputes."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.OPEN
        )
        self.assertTrue(dispute.is_active)

    def test_is_active_for_under_review_disputes(self):
        """Test that is_active returns True for UNDER_REVIEW disputes."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.UNDER_REVIEW
        )
        self.assertTrue(dispute.is_active)

    def test_is_not_active_for_resolved_disputes(self):
        """Test that is_active returns False for RESOLVED disputes."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.RESOLVED
        )
        self.assertFalse(dispute.is_active)

    def test_unique_constraint_one_active_dispute_per_user(self):
        """Test that only one active dispute per user per bill is allowed."""
        create_bill_dispute(
            bill=self.bill,
            user=self.user,
            status=BillDisputeStatus.OPEN
        )
        
        with self.assertRaises(IntegrityError):
            create_bill_dispute(
                bill=self.bill,
                user=self.user,
                status=DisputeStatus.OPEN,
                reason="Another active dispute"
            )

    def test_days_since_created_calculation(self):
        """Test that days_since_created property calculates correctly."""
        dispute = create_bill_dispute(
            bill=self.bill,
            user=self.user
        )
        days = dispute.days_since_created
        self.assertEqual(days, 0)
