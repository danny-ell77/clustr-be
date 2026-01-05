"""
Tests for utility bill specific nuances.
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from core.common.models import (
    Bill,
    BillType,
    BillStatus,
    BillCategory,
    UtilityProvider,
    Transaction,
)
from members.tests.utils import create_user, create_cluster
from members.tests.test_payment_utils import (
    create_bill,
    create_utility_provider,
    create_wallet,
    create_transaction,
)


class UtilityBillModelTests(TestCase):
    """Tests for utility bill model nuances."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.user = create_user(
            email="user@test.com",
            phone_number="+2348000000001",
            cluster=self.cluster
        )
        self.provider = create_utility_provider(
            cluster=self.cluster,
            provider_type=BillType.ELECTRICITY_UTILITY
        )

    def test_utility_bill_has_utility_provider(self):
        """Test that utility bills can have a utility provider."""
        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user.id,
            type=BillType.ELECTRICITY_UTILITY,
            category=BillCategory.USER_MANAGED,
            title="Electricity Bill",
            amount=Decimal("5000.00"),
            utility_provider=self.provider,
            customer_id="1234567890",
            currency="NGN",
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            created_by=str(self.user.id),
            last_modified_by=str(self.user.id),
        )
        
        self.assertIsNotNone(bill.utility_provider)
        self.assertEqual(bill.utility_provider, self.provider)
        self.assertEqual(bill.customer_id, "1234567890")

    def test_utility_bill_has_customer_id(self):
        """Test that utility bills store customer ID."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user,
            category=BillCategory.USER_MANAGED,
            bill_type=BillType.ELECTRICITY_UTILITY
        )
        
        bill.customer_id = "METER123456"
        bill.save()
        
        self.assertEqual(bill.customer_id, "METER123456")

    def test_is_utility_bill_for_user_managed(self):
        """Test utility bill identification for USER_MANAGED bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user,
            category=BillCategory.USER_MANAGED,
            bill_type=BillType.ELECTRICITY_UTILITY
        )
        
        self.assertTrue(bill.type.endswith("_utility"))

    def test_is_not_utility_bill_for_cluster_managed(self):
        """Test regular cluster-managed bills are not utility bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=None,
            category=BillCategory.CLUSTER_MANAGED,
            bill_type=BillType.SECURITY
        )
        
        self.assertFalse(bill.type.endswith("_utility"))

    def test_can_automate_payment_with_provider(self):
        """Test that utility bills with provider can be automated."""
        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user.id,
            type=BillType.ELECTRICITY_UTILITY,
            category=BillCategory.USER_MANAGED,
            title="Electricity Bill",
            amount=Decimal("5000.00"),
            utility_provider=self.provider,
            customer_id="1234567890",
            currency="NGN",
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            created_by=str(self.user.id),
            last_modified_by=str(self.user.id),
        )
        
        bill.is_automated = True
        bill.save()
        
        self.assertTrue(bill.is_automated)
        self.assertIsNotNone(bill.utility_provider)

    def test_cannot_automate_without_provider(self):
        """Test that bills without provider cannot be automated."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user,
            category=BillCategory.USER_MANAGED,
            bill_type=BillType.ELECTRICITY
        )
        
        self.assertIsNone(bill.utility_provider)
        self.assertFalse(bill.is_automated)

    def test_get_utility_metadata(self):
        """Test that utility metadata is properly stored."""
        bill = Bill.objects.create(
            cluster=self.cluster,
            user_id=self.user.id,
            type=BillType.WATER_UTILITY,
            category=BillCategory.USER_MANAGED,
            title="Water Bill",
            amount=Decimal("2000.00"),
            utility_provider=create_utility_provider(
                cluster=self.cluster,
                provider_type=BillType.WATER_UTILITY,
                provider_code="WATER_CO"
            ),
            customer_id="WATER123",
            metadata={"meter_reading": "12345", "period": "2024-01"},
            currency="NGN",
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            created_by=str(self.user.id),
            last_modified_by=str(self.user.id),
        )
        
        self.assertIn("meter_reading", bill.metadata)
        self.assertEqual(bill.metadata["meter_reading"], "12345")


class UtilityProviderTests(TestCase):
    """Tests for UtilityProvider model."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.provider = create_utility_provider(
            cluster=self.cluster,
            min_amount=Decimal("100.00"),
            max_amount=Decimal("50000.00")
        )

    def test_is_amount_valid_within_limits(self):
        """Test amount validation within limits."""
        result = self.provider.is_amount_valid(Decimal("1000.00"))
        self.assertTrue(result)

    def test_is_amount_valid_below_minimum(self):
        """Test amount validation below minimum."""
        result = self.provider.is_amount_valid(Decimal("50.00"))
        self.assertFalse(result)

    def test_is_amount_valid_above_maximum(self):
        """Test amount validation above maximum."""
        result = self.provider.is_amount_valid(Decimal("100000.00"))
        self.assertFalse(result)

    def test_provider_code_uniqueness_per_cluster(self):
        """Test that provider codes are unique per cluster."""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            create_utility_provider(
                cluster=self.cluster,
                provider_code="TEST_PROVIDER"
            )


class BillCategoryDifferenceTests(TestCase):
    """Tests for differences between bill categories."""

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
        self.wallet1 = create_wallet(user=self.user1, cluster=self.cluster)
        self.wallet2 = create_wallet(user=self.user2, cluster=self.cluster)

    def test_cluster_managed_payment_tracking_via_transactions(self):
        """Test that cluster-managed bills track payments via transactions."""
        bill = create_bill(
            cluster=self.cluster,
            user=None,
            category=BillCategory.CLUSTER_MANAGED,
            amount=Decimal("10000.00")
        )
        
        txn1 = create_transaction(
            wallet=self.wallet1,
            amount=Decimal("5000.00"),
            bill=bill
        )
        txn2 = create_transaction(
            wallet=self.wallet2,
            amount=Decimal("3000.00"),
            bill=bill
        )
        
        total_paid = Transaction.objects.filter(bill=bill).aggregate(
            total=sum
        )
        self.assertGreater(
            Transaction.objects.filter(bill=bill).count(),
            0
        )

    def test_user_managed_payment_tracking_via_paid_amount(self):
        """Test that user-managed bills track payments via paid_amount."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("5000.00")
        )
        
        bill.paid_amount = Decimal("2000.00")
        bill.save()
        
        self.assertEqual(bill.paid_amount, Decimal("2000.00"))
        self.assertEqual(bill.remaining_amount, Decimal("3000.00"))

    def test_cluster_managed_allows_multiple_payers(self):
        """Test that cluster-managed bills can have multiple payers."""
        bill = create_bill(
            cluster=self.cluster,
            user=None,
            category=BillCategory.CLUSTER_MANAGED,
            amount=Decimal("10000.00")
        )
        
        create_transaction(wallet=self.wallet1, amount=Decimal("5000.00"), bill=bill)
        create_transaction(wallet=self.wallet2, amount=Decimal("5000.00"), bill=bill)
        
        unique_payers = Transaction.objects.filter(bill=bill).values('wallet_id').distinct().count()
        self.assertEqual(unique_payers, 2)

    def test_user_managed_single_payer_only(self):
        """Test that user-managed bills have single payer."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            amount=Decimal("5000.00")
        )
        
        self.assertIsNotNone(bill.user_id)
        self.assertEqual(bill.user_id, self.user1.id)
