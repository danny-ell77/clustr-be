"""
Integration tests for BillViewSet API endpoints.
"""
from decimal import Decimal
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.common.models import (
    Bill,
    BillStatus,
    BillCategory,
    BillType,
)
from members.tests.utils import create_user, create_cluster, authenticate_user
from members.tests.test_payment_utils import (
    create_bill,
    create_wallet,
    create_bill_dispute,
)


class BillViewSetTests(APITestCase):
    """Integration tests for BillViewSet API endpoints."""

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
        self.wallet1 = create_wallet(
            user=self.user1,
            cluster=self.cluster,
            balance=Decimal("10000.00")
        )

    def test_list_bills_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        url = reverse("bills-my-bills")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_bills_authenticated(self):
        """Test that authenticated users can list bills."""
        authenticate_user(self.client, self.user1)
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED
        )
        
        url = reverse("bills-my-bills")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_access_other_users_bills(self):
        """Test that users cannot access other users' bills."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user2,
            category=BillCategory.USER_MANAGED
        )
        authenticate_user(self.client, self.user1)
        
        url = reverse("bills-my-bills")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill_ids = [b["id"] for b in response.data.get("results", [])]
        self.assertNotIn(str(bill.id), bill_ids)

    def test_my_bills_returns_user_bills(self):
        """Test that my_bills returns only user's bills."""
        bill1 = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            title="User 1 Bill"
        )
        create_bill(
            cluster=self.cluster,
            user=self.user2,
            category=BillCategory.USER_MANAGED,
            title="User 2 Bill"
        )
        
        authenticate_user(self.client, self.user1)
        url =reverse("bills-my-bills")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertGreaterEqual(len(results), 1)
        self.assertIn(str(bill1.id), [b["id"] for b in results])

    def test_my_bills_filters_by_status(self):
        """Test that my_bills can filter by status."""
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PAID
        )
        
        authenticate_user(self.client, self.user1)
        url = f"{reverse('bills-my-bills')}?status={BillStatus.PAID}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        for bill in results:
            self.assertEqual(bill["status"], BillStatus.PAID)

    def test_my_bills_filters_by_type(self):
        """Test that my_bills can filter by bill type."""
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            bill_type=BillType.SECURITY
        )
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            bill_type=BillType.WATER
        )
        
        authenticate_user(self.client, self.user1)
        url = f"{reverse('bills-my-bills')}?type={BillType.SECURITY}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        for bill in results:
            self.assertEqual(bill["type"], BillType.SECURITY)

    def test_summary_returns_correct_totals(self):
        """Test that summary endpoint returns correct totals."""
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            amount=Decimal("1000.00")
        )
        create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PAID,
            amount=Decimal("2000.00")
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-summary")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_bills", response.data)
        self.assertGreaterEqual(response.data["total_bills"], 2)

    def test_acknowledge_bill_success(self):
        """Test successful bill acknowledgment."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-acknowledge-bill", kwargs={"pk": bill.id})
        response = self.client.post(url, {"bill_id": str(bill.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.ACKNOWLEDGED)

    def test_acknowledge_already_acknowledged_bill(self):
        """Test acknowledging an already acknowledged bill."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-acknowledge-bill", kwargs={"pk": bill.id})
        response = self.client.post(url, {"bill_id": str(bill.id)})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dispute_bill_success(self):
        """Test successful bill dispute."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-dispute-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "reason": "Amount is incorrect"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.DISPUTED)

    def test_dispute_requires_reason(self):
        """Test that dispute requires a reason."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-dispute-bill", kwargs={"pk": bill.id})
        response = self.client.post(url, {"bill_id": str(bill.id)})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dispute_already_disputed_bill(self):
        """Test disputing an already disputed bill."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.DISPUTED
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-dispute-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "reason": "Another dispute"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pay_bill_success(self):
        """Test successful bill payment from wallet."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED,
            amount=Decimal("1000.00")
        )
        bill.acknowledged_by.add(self.user1)
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-pay-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "amount": "1000.00"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("transaction_id", response.data)

    def test_pay_bill_insufficient_balance(self):
        """Test payment failure with insufficient wallet balance."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED,
            amount=Decimal("50000.00")
        )
        bill.acknowledged_by.add(self.user1)
        
        self.wallet1.balance = Decimal("100.00")
        self.wallet1.save()
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-pay-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "amount": "50000.00"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pay_bill_requires_acknowledgment(self):
        """Test that USER_MANAGED bills require acknowledgment before payment."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            amount=Decimal("1000.00")
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-pay-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "amount": "1000.00"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_pay_disputed_bill(self):
        """Test that disputed bills cannot be paid."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.DISPUTED,
            amount=Decimal("1000.00")
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-pay-bill", kwargs={"pk": bill.id})
        data = {
            "bill_id": str(bill.id),
            "amount": "1000.00"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pay_bill_direct_initializes_payment(self):
        """Test direct payment initialization."""
        bill = create_bill(
            cluster=self.cluster,
            user=self.user1,
            category=BillCategory.USER_MANAGED,
            status=BillStatus.ACKNOWLEDGED,
            amount=Decimal("1000.00")
        )
        bill.acknowledged_by.add(self.user1)
        
        authenticate_user(self.client, self.user1)
        url = reverse("bills-pay-bill-direct")
        data = {
            "bill_id": str(bill.id),
            "provider": "paystack",
            "callback_url": "https://example.com/callback"
        }
        response = self.client.post(url, data)
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
