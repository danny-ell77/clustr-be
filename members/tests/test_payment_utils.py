"""
Utility functions for payment-related tests.
"""
from decimal import Decimal
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from core.common.models import (
    Bill,
    BillType,
    BillStatus,
    BillCategory,
    BillDispute,
    DisputeStatus,
    Wallet,
    WalletStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
    RecurringPayment,
    RecurringPaymentStatus,
    RecurringPaymentFrequency,
    UtilityProvider,
    Cluster,
)
from accounts.models import AccountUser


def create_wallet(
    user: AccountUser,
    cluster: Cluster,
    balance: Decimal = Decimal("1000.00"),
    currency: str = "NGN",
    status: str = WalletStatus.ACTIVE,
):
    """
    Create and return a test wallet.
    """
    wallet, created = Wallet.objects.get_or_create(
        cluster=cluster,
        user_id=user.id,
        defaults={
            "balance": balance,
            "available_balance": balance,
            "currency": currency,
            "status": status,
            "created_by": str(user.id),
            "last_modified_by": str(user.id),
        },
    )
    
    if not created and balance != wallet.balance:
        wallet.balance = balance
        wallet.available_balance = balance
        wallet.save(update_fields=["balance", "available_balance"])
    
    return wallet


def create_bill(
    cluster: Cluster,
    user: Optional[AccountUser] = None,
    bill_type: str = BillType.SECURITY,
    category: str = BillCategory.CLUSTER_MANAGED,
    amount: Decimal = Decimal("5000.00"),
    status: str = BillStatus.PENDING,
    title: str = "Test Bill",
    due_date: Optional[timezone.datetime] = None,
    created_by: Optional[str] = None,
):
    """
    Create and return a test bill.
    """
    if due_date is None:
        due_date = timezone.now() + timedelta(days=7)
    
    bill_data = {
        "cluster": cluster,
        "type": bill_type,
        "category": category,
        "title": title,
        "amount": amount,
        "currency": "NGN",
        "due_date": due_date,
        "created_by": created_by or (str(user.id) if user else "admin"),
        "last_modified_by": created_by or (str(user.id) if user else "admin"),
    }
    
    if user and category == BillCategory.USER_MANAGED:
        bill_data["user_id"] = user.id
    
    bill = Bill.objects.create(**bill_data)

    # Simulate status for tests
    if status == BillStatus.PAID:
        bill.paid_amount = amount
        bill.paid_at = timezone.now()
        bill.save(update_fields=["paid_amount", "paid_at"])
    elif status == BillStatus.PARTIALLY_PAID:
        bill.paid_amount = amount / 2
        bill.save(update_fields=["paid_amount"])
    elif status == BillStatus.ACKNOWLEDGED and user:
        bill.acknowledge(user)
    elif status == BillStatus.PENDING_ACKNOWLEDGMENT:
        # This is the default state for user managed bills before ack
        pass

    return bill


def create_utility_provider(
    cluster: Cluster,
    provider_type: str = BillType.ELECTRICITY_UTILITY,
    provider_code: str = "TEST_PROVIDER",
    min_amount: Decimal = Decimal("100.00"),
    max_amount: Decimal = Decimal("50000.00"),
    is_active: bool = True,
):

    """
    Create and return a test utility provider.
    """
    provider = UtilityProvider.objects.create(
        cluster=cluster,
        provider_type=provider_type,
        provider_name=f"Test {provider_type.title()} Provider",
        provider_code=provider_code,
        api_endpoint="https://api.test-provider.com",
        min_amount=min_amount,
        max_amount=max_amount,
        is_active=is_active,
        created_by="admin",
        last_modified_by="admin",
    )
    return provider


def create_bill_dispute(
    bill: Bill,
    user: AccountUser,
    reason: str = "Bill amount is incorrect",
    status: str = DisputeStatus.OPEN,
):
    """
    Create and return a test bill dispute.
    """
    dispute = BillDispute.objects.create(
        bill=bill,
        user_id=user.id,
        reason=reason,
        status=status,
        created_by=str(user.id),
        last_modified_by=str(user.id),
    )
    return dispute


def create_recurring_payment(
    wallet: Wallet,
    title: str = "Test Recurring Payment",
    amount: Decimal = Decimal("1000.00"),
    frequency: str = RecurringPaymentFrequency.MONTHLY,
    bill: Optional[Bill] = None,
    utility_provider: Optional[UtilityProvider] = None,
    customer_id: Optional[str] = None,
    start_date: Optional[timezone.datetime] = None,
    end_date: Optional[timezone.datetime] = None,
    status: str = RecurringPaymentStatus.ACTIVE,
):
    """
    Create and return a test recurring payment.
    """
    if start_date is None:
        start_date = timezone.now()
    
    recurring_payment = RecurringPayment.objects.create(
        cluster=wallet.cluster,
        user_id=wallet.user_id,
        wallet=wallet,
        bill=bill,
        title=title,
        amount=amount,
        currency=wallet.currency,
        frequency=frequency,
        status=status,
        start_date=start_date,
        end_date=end_date,
        next_payment_date=start_date,
        utility_provider=utility_provider,
        customer_id=customer_id,
        created_by=str(wallet.user_id),
        last_modified_by=str(wallet.user_id),
    )
    return recurring_payment


def create_transaction(
    wallet: Wallet,
    transaction_type: str = TransactionType.DEPOSIT,
    amount: Decimal = Decimal("1000.00"),
    status: str = TransactionStatus.COMPLETED,
    bill: Optional[Bill] = None,
    description: str = "Test transaction",
):
    """
    Create and return a test transaction.
    """
    transaction = Transaction.objects.create(
        cluster=wallet.cluster,
        wallet=wallet,
        type=transaction_type,
        amount=amount,
        currency=wallet.currency,
        status=status,
        bill=bill,
        description=description,
        created_by=str(wallet.user_id),
        last_modified_by=str(wallet.user_id),
    )
    
    if status == TransactionStatus.COMPLETED:
        transaction.processed_at = timezone.now()
        transaction.save(update_fields=["processed_at"])
    
    return transaction
