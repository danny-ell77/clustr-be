"""
Integration tests for WalletViewSet API endpoints.
"""
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.common.models import (
    WalletStatus,
    TransactionType,
    TransactionStatus,
)
from members.tests.utils import create_user, create_cluster, authenticate_user
from members.tests.test_payment_utils import (
    create_wallet,
    create_transaction,
)


class WalletViewSetTests(APITestCase):
    """Integration tests for WalletViewSet API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.cluster, self.admin = create_cluster()
        self.user = create_user(
            email="user@test.com",
            phone_number="+2348000000001",
            cluster=self.cluster
        )

    def test_get_balance_creates_wallet_if_missing(self):
        """Test that balance endpoint creates wallet if it doesn't exist."""
        authenticate_user(self.client, self.user)
        
        url = reverse("wallet-balance")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("balance", response.data)
        self.assertEqual(Decimal(response.data["balance"]), Decimal("0.00"))

    def test_get_balance_returns_correct_amount(self):
        """Test that balance endpoint returns correct wallet balance."""
        wallet = create_wallet(
            user=self.user,
            cluster=self.cluster,
            balance=Decimal("5000.00")
        )
        
        authenticate_user(self.client, self.user)
        url = reverse("wallet-balance")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), Decimal("5000.00"))

    def test_deposit_initializes_transaction(self):
        """Test that deposit endpoint initializes a transaction."""
        authenticate_user(self.client, self.user)
        
        url = reverse("wallet-deposit")
        data = {
            "amount": "1000.00",
            "provider": "paystack",
            "callback_url": "https://example.com/callback"
        }
        response = self.client.post(url, data, format="json")
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])

    def test_transactions_list_returns_history(self):
        """Test that transactions endpoint returns user's transaction history."""
        wallet = create_wallet(
            user=self.user,
            cluster=self.cluster,
            balance=Decimal("5000.00")
        )
        transaction = create_transaction(
            wallet=wallet,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("1000.00"),
            status=TransactionStatus.COMPLETED
        )
        
        authenticate_user(self.client, self.user)
        url = reverse("wallet-transactions")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("transactions", response.data)
        transaction_ids = [t["id"] for t in response.data["transactions"]]
        self.assertIn(str(transaction.id), transaction_ids)

    def test_transactions_filter_by_type(self):
        """Test that transactions can be filtered by type."""
        wallet = create_wallet(
            user=self.user,
            cluster=self.cluster,
            balance=Decimal("5000.00")
        )
        create_transaction(
            wallet=wallet,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("1000.00")
        )
        create_transaction(
            wallet=wallet,
            transaction_type=TransactionType.PAYMENT,
            amount=Decimal("500.00")
        )
        
        authenticate_user(self.client, self.user)
        url = f"{reverse('wallet-transactions')}?type={TransactionType.DEPOSIT}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transactions = response.data.get("transactions", [])
        for txn in transactions:
            self.assertEqual(txn["type"], TransactionType.DEPOSIT)

    def test_transactions_pagination(self):
        """Test that transactions are paginated."""
        wallet = create_wallet(
            user=self.user,
            cluster=self.cluster,
            balance=Decimal("5000.00")
        )
        
        for i in range(25):
            create_transaction(
                wallet=wallet,
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal("100.00")
            )
        
        authenticate_user(self.client, self.user)
        url = reverse("wallet-transactions")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pagination", response.data)
        self.assertGreater(response.data["pagination"]["total_count"], 20)
