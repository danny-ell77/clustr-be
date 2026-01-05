"""
Integration tests for RecurringPaymentViewSet API endpoints.
"""
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.common.models import (
    RecurringPaymentStatus,
    RecurringPaymentFrequency,
    BillCategory,
)
from members.tests.utils import create_user, create_cluster, authenticate_user
from members.tests.test_payment_utils import (
    create_wallet,
    create_bill,
    create_recurring_payment,
)


class RecurringPaymentViewSetTests(APITestCase):
    """Integration tests for RecurringPaymentViewSet API endpoints."""

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
        self.wallet2 = create_wallet(
            user=self.user2,
            cluster=self.cluster,
            balance=Decimal("5000.00")
        )

    def test_create_recurring_payment_success(self):
        """Test successful creation of recurring payment."""
        authenticate_user(self.client, self.user1)
        
        url = reverse("recurringpayment-list")
        data = {
            "title": "Monthly Rent",
            "amount": "5000.00",
            "frequency": RecurringPaymentFrequency.MONTHLY,
            "start_date": timezone.now().isoformat(),
        }
        response = self.client.post(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["title"], "Monthly Rent")

    def test_create_recurring_payment_invalid_data(self):
        """Test creation fails with invalid data."""
        authenticate_user(self.client, self.user1)
        
        url = reverse("recurringpayment-list")
        data = {
            "title": "Invalid Payment",
            "amount": "-100.00",
            "frequency": RecurringPaymentFrequency.MONTHLY,
        }
        response = self.client.post(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_recurring_payment_missing_wallet(self):
        """Test creation handles missing wallet gracefully."""
        user_no_wallet = create_user(
            email="nowallet@test.com",
            phone_number="+2348000000099",
            cluster=self.cluster
        )
        authenticate_user(self.client, user_no_wallet)
        
        url = reverse("recurringpayment-list")
        data = {
            "title": "Monthly Payment",
            "amount": "1000.00",
            "frequency": RecurringPaymentFrequency.MONTHLY,
            "start_date": timezone.now().isoformat(),
        }
        response = self.client.post(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_my_payments(self):
        """Test listing user's recurring payments."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet1,
            title="My Recurring Payment"
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("recurringpayment-my-payments")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment_ids = [p["id"] for p in response.data.get("results", [])]
        self.assertIn(str(recurring_payment.id), payment_ids)

    def test_pause_payment_success(self):
        """Test successful pausing of recurring payment."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet1,
            status=RecurringPaymentStatus.ACTIVE
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("recurringpayment-pause-payment")
        data = {"payment_id": str(recurring_payment.id)}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recurring_payment.refresh_from_db()
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.PAUSED)

    def test_resume_payment_success(self):
        """Test successful resuming of paused recurring payment."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet1,
            status=RecurringPaymentStatus.PAUSED
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("recurringpayment-resume-payment")
        data = {"payment_id": str(recurring_payment.id)}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recurring_payment.refresh_from_db()
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.ACTIVE)

    def test_cancel_payment_success(self):
        """Test successful cancellation of recurring payment."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet1,
            status=RecurringPaymentStatus.ACTIVE
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("recurringpayment-cancel-payment")
        data = {"payment_id": str(recurring_payment.id)}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recurring_payment.refresh_from_db()
        self.assertEqual(recurring_payment.status, RecurringPaymentStatus.CANCELLED)

    def test_cannot_manage_other_users_payments(self):
        """Test that users cannot manage other users' recurring payments."""
        recurring_payment = create_recurring_payment(
            wallet=self.wallet2,
            status=RecurringPaymentStatus.ACTIVE
        )
        
        authenticate_user(self.client, self.user1)
        url = reverse("recurringpayment-pause-payment")
        data = {"payment_id": str(recurring_payment.id)}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
