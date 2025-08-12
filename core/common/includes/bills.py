"""
Bills utilities for ClustR application.
Refactored from BillManager static methods to pure functions.
"""

import logging
from decimal import Decimal
from typing import Optional, Any
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
import itertools

from core.common.models import (
    Bill,
    BillStatus,
    BillType,
    BillCategory,
    Transaction,
    TransactionType,
    TransactionStatus,
    Wallet,
)
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

logger = logging.getLogger("clustr")


def create_cluster_wide(
    cluster,
    title: str,
    amount: Decimal,
    bill_type: BillType,
    due_date,
    description: str = None,
    allow_payment_after_due: bool = True,
    created_by: str = None,
    metadata: Optional[dict] = None,
) -> Bill:
    """
    Create a new cluster-wide bill that applies to all cluster members.
    This creates only ONE record regardless of the number of users in the cluster.

    Args:
        cluster: Estate object
        title: Bill title
        amount: Bill amount
        bill_type: Type of bill
        due_date: Bill due date
        description: Bill description
        allow_payment_after_due: Whether payment is allowed after due date
        created_by: ID of the user creating the bill
        metadata: Additional bill metadata

    Returns:
        Bill: Created bill object
    """
    bill = Bill.objects.create(
        cluster=cluster,
        user_id=None,  # Estate-wide bills have no specific user
        title=title,
        category=BillCategory.CLUSTER_MANAGED,
        description=description,
        type=bill_type,
        amount=amount,
        due_date=due_date,
        allow_payment_after_due=allow_payment_after_due,
        metadata=metadata or {},
        created_by=created_by,
        last_modified_by=created_by,
    )

    logger.info(
        f"Estate-wide bill created: {bill.bill_number} for cluster {cluster.name}"
    )

    # Send notification to all cluster members
    send_cluster_wide_bill_notification(bill)

    return bill


def create_user_specific(
    cluster,
    user_id: str,
    title: str,
    amount: Decimal,
    bill_type: BillType,
    due_date,
    description: str = None,
    allow_payment_after_due: bool = True,
    created_by: str = None,
    metadata: Optional[dict] = None,
) -> Bill:
    """
    Create a new user-specific bill that applies to only one user.

    Args:
        cluster: Estate object
        user_id: ID of the user the bill is for
        title: Bill title
        amount: Bill amount
        bill_type: Type of bill
        due_date: Bill due date
        description: Bill description
        allow_payment_after_due: Whether payment is allowed after due date
        created_by: ID of the user creating the bill
        metadata: Additional bill metadata

    Returns:
        Bill: Created bill object
    """
    bill = Bill.objects.create(
        cluster=cluster,
        user_id=user_id,  # User-specific bills target a specific user
        title=title,
        description=description,
        type=bill_type,
        category=BillCategory.USER_MANAGED,
        amount=amount,
        due_date=due_date,
        allow_payment_after_due=allow_payment_after_due,
        metadata=metadata or {},
        created_by=created_by,
        last_modified_by=created_by,
    )

    logger.info(f"User-specific bill created: {bill.bill_number} for user {user_id}")

    # Send notification to the specific user
    send_user_specific_bill_notification(bill)

    return bill


def get_summary(cluster, user) -> dict[str, Any]:
    """
    Get a financial summary for a user, including their share of cluster bills.

    Args:
        cluster: The cluster to search within.
        user: The user for whom to generate the summary.

    Returns:
        A dictionary containing the user's bill summary.
    """
    # User-specific bills are straightforward
    user_bills = Bill.objects.filter(cluster=cluster, user_id=user.id)

    # Cluster-wide bills require per-user calculation
    cluster_bills = Bill.objects.filter(
        cluster=cluster, category=BillCategory.CLUSTER_MANAGED
    )

    total_amount_due = user_bills.exclude(status=BillStatus.PAID).aggregate(
        total=Sum("amount") - Sum("paid_amount")
    )["total"] or Decimal("0.00")

    overdue_count = (
        user_bills.filter(due_date__lt=timezone.now())
        .exclude(status=BillStatus.PAID)
        .count()
    )

    for bill in cluster_bills:
        paid_amount = bill.get_user_payment_amount(user)
        remaining = bill.amount - paid_amount
        if remaining > 0:
            total_amount_due += remaining
            if bill.due_date < timezone.now():
                overdue_count += 1

    summary = {
        "total_bills": user_bills.count()
        + cluster_bills.filter(acknowledged_by=user).count(),
        "pending_bills": user_bills.filter(
            status=BillStatus.PENDING
        ).count(),  # Note: Pending for cluster bills is per-user
        "overdue_bills": overdue_count,
        "paid_bills": user_bills.filter(
            status=BillStatus.PAID
        ).count(),  # Note: Paid for cluster bills is per-user
        "total_amount_due": total_amount_due,
        "total_paid": user_bills.filter(status=BillStatus.PAID).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00"),  # Note: Needs adjustment for cluster bills
    }

    return summary


def acknowledge(bill: Bill, acknowledged_by: str) -> bool:
    """
    Acknowledge a bill.

    Args:
        bill: Bill to acknowledge
        acknowledged_by: ID of the user acknowledging the bill

    Returns:
        bool: True if acknowledgment was successful
    """
    if bill.acknowledge(acknowledged_by):
        logger.info(f"Bill {bill.bill_number} acknowledged by user {acknowledged_by}")
        return True
    return False


def dispute(bill: Bill, disputed_by: str, reason: str) -> bool:
    """
    Dispute a bill.

    Args:
        bill: Bill to dispute
        disputed_by: ID of the user disputing the bill
        reason: Reason for dispute

    Returns:
        bool: True if dispute was successful
    """
    if bill.dispute(disputed_by, reason):
        logger.info(f"Bill {bill.bill_number} disputed by user {disputed_by}: {reason}")

        # Send dispute notification to admins
        send_bill_disputed_notification(bill)

        return True
    return False


@transaction.atomic
def process_payment(bill: Bill, wallet: Wallet, amount: Decimal, user, idempotency_key: str = None) -> Transaction:
    """
    Process payment for a bill using wallet balance.
    This handles wallet-to-wallet payments where user pays from their wallet.

    Args:
        bill: Bill to pay
        wallet: Wallet to debit
        amount: Amount to pay
        user: User making the payment

    Returns:
        Payment transaction object.
    """
    if not bill.can_be_paid_by(user):
        raise ValueError("User is not authorized to pay this bill at this time.")

    if bill.category == BillCategory.CLUSTER_MANAGED:
        paid_amount = bill.get_user_payment_amount(user)
        remaining_share = bill.amount - paid_amount
        payment_amount = amount or remaining_share
        if payment_amount > remaining_share:
            raise ValueError(
                f"Payment amount {payment_amount} exceeds remaining share {remaining_share}."
            )
    else:  # User-managed bill
        remaining_amount = bill.amount - bill.paid_amount
        payment_amount = amount or remaining_amount
        if payment_amount > remaining_amount:
            raise ValueError(
                f"Payment amount {payment_amount} exceeds remaining amount {remaining_amount}."
            )

    if payment_amount <= 0:
        raise ValueError("Payment amount must be greater than 0.")

    if not wallet.has_sufficient_balance(payment_amount):
        raise ValueError("Insufficient wallet balance.")

    # Check for duplicate payment using idempotency key
    if idempotency_key:
        existing_transaction = Transaction.objects.filter(
            idempotency_key=idempotency_key,
            wallet=wallet
        ).first()
        if existing_transaction:
            logger.info(f"Duplicate payment attempt detected with idempotency key: {idempotency_key}")
            return existing_transaction

    # Create transaction (pending initially)
    transaction = Transaction.objects.create(
        cluster=wallet.cluster,
        wallet=wallet,
        type=TransactionType.BILL_PAYMENT,
        amount=payment_amount,
        currency=wallet.currency,
        description=f"Bill payment: {bill.title}",
        status=TransactionStatus.PENDING,
        created_by=user.id,
        last_modified_by=user.id,
        metadata={"bill_id": str(bill.id), "payment_method": "wallet"},
        idempotency_key=idempotency_key,
    )

    # Process the payment - this will debit wallet and credit cluster
    bill.add_payment(payment_amount, transaction)
    
    # Mark transaction as completed (no wallet update needed - already done in add_payment)
    transaction.status = TransactionStatus.COMPLETED
    transaction.processed_at = timezone.now()
    transaction.save(update_fields=['status', 'processed_at'])

    logger.info(
        f"Bill payment processed: {transaction.transaction_id} for bill {bill.bill_number}"
    )

    # Send payment confirmation
    send_payment_confirmation(bill, transaction)

    return transaction


def update_status(bill: Bill, new_status: BillStatus, updated_by: str = None) -> bool:
    """
    Update bill status.

    Args:
        bill: Bill to update
        new_status: New status for the bill
        updated_by: ID of the user updating the status

    Returns:
        bool: True if update was successful
    """
    old_status = bill.status
    bill.status = new_status
    bill.last_modified_by = updated_by
    bill.save()

    logger.info(
        f"Bill {bill.bill_number} status updated from {old_status} to {new_status}"
    )

    # Send status change notification
    send_bill_status_notification(bill, old_status, new_status)

    return True


# Bill notification helper functions
def send_cluster_wide_bill_notification(bill: Bill) -> bool:
    """Send notification for cluster-wide bill creation."""
    try:
        # Get all cluster members
        from accounts.models import AccountUser

        cluster_members = AccountUser.objects.filter(cluster=bill.cluster)

        def _chunk(iterable, size):
            it = iter(iterable)
            while chunk := list(itertools.islice(it, size)):
                yield chunk

        for members in _chunk(cluster_members, 100):
            recipients = list(members)
            notifications.send(
                event_name=NotificationEvents.BILL_CREATED,
                recipients=recipients,
                cluster=bill.cluster,
                context={
                    "bill_number": bill.bill_number,
                    "bill_title": bill.title,
                    "amount": str(bill.amount),
                    "due_date": (
                        bill.due_date.strftime("%Y-%m-%d")
                        if bill.due_date
                        else "Not set"
                    ),
                    "description": bill.description or "No description provided",
                    "bill_type": "Cluster-wide",
                },
            )
        return True

    except Exception as e:
        logger.error(f"Failed to send cluster-wide bill notification: {e}")
        return False


def send_user_specific_bill_notification(bill: Bill) -> bool:
    """Send notification for user-specific bill creation."""
    try:
        from accounts.models import AccountUser

        user = AccountUser.objects.get(id=bill.user_id)

        notifications.send(
            event_name=NotificationEvents.BILL_CREATED,
            recipients=[user],
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "amount": str(bill.amount),
                "due_date": (
                    bill.due_date.strftime("%Y-%m-%d") if bill.due_date else "Not set"
                ),
                "description": bill.description or "No description provided",
                "bill_type": "Personal",
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send user-specific bill notification: {e}")
        return False


def send_payment_confirmation(bill: Bill, transaction: Transaction) -> bool:
    """Send payment confirmation notification."""
    try:
        from accounts.models import AccountUser

        user = AccountUser.objects.get(id=transaction.created_by)

        notifications.send(
            event_name=NotificationEvents.PAYMENT_SUCCESSFUL,
            recipients=[user],
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "payment_amount": str(transaction.amount),
                "transaction_id": transaction.transaction_id,
                "payment_date": transaction.processed_at.strftime("%Y-%m-%d %H:%M"),
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send payment confirmation: {e}")
        return False


def send_bill_disputed_notification(bill: Bill) -> bool:
    """Send bill dispute notification to admins."""
    try:
        from accounts.models import AccountUser

        admins = AccountUser.objects.filter(cluster=bill.cluster, is_staff=True)

        notifications.send(
            event_name=NotificationEvents.BILL_DISPUTED,
            recipients=list(admins),
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "amount": str(bill.amount),
                "dispute_reason": bill.dispute_reason or "No reason provided",
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send bill dispute notification: {e}")
        return False


def send_bill_status_notification(bill: Bill, old_status: str, new_status: str) -> bool:
    """Send bill status change notification."""
    try:
        from accounts.models import AccountUser

        recipients = []
        if bill.user_id:
            # User-specific bill
            user = AccountUser.objects.get(id=bill.user_id)
            recipients.append(user)
        else:
            # Cluster-wide bill
            cluster_members = AccountUser.objects.filter(cluster=bill.cluster)
            recipients.extend(cluster_members)

        notifications.send(
            event_name=NotificationEvents.BILL_STATUS_CHANGED,
            recipients=recipients,
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send bill status notification: {e}")
        return False


def check_and_update_overdue(cluster) -> int:
    """
    Check and update overdue bills for a cluster.
    
    Args:
        cluster: Cluster to check bills for
        
    Returns:
        Number of bills marked as overdue
    """
    from django.utils import timezone
    
    now = timezone.now()
    overdue_bills = Bill.objects.filter(
        cluster=cluster,
        due_date__lt=now,
        status=BillStatus.PENDING
    )
    
    count = 0
    for bill in overdue_bills:
        bill.status = BillStatus.OVERDUE
        bill.save()
        count += 1
        
        # Send overdue notification
        send_overdue_notification(bill)
    
    logger.info(f"Marked {count} bills as overdue for cluster {cluster.name}")
    return count


def send_reminders(cluster, days_before_due: int = 3) -> int:
    """
    Send bill reminders for bills approaching due date.
    
    Args:
        cluster: Cluster to send reminders for
        days_before_due: Number of days before due date to send reminder
        
    Returns:
        Number of reminders sent
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    reminder_date = now + timedelta(days=days_before_due)
    
    bills_due_soon = Bill.objects.filter(
        cluster=cluster,
        due_date__gte=now,
        due_date__lte=reminder_date,
        status=BillStatus.PENDING
    )
    
    count = 0
    for bill in bills_due_soon:
        if send_reminder_notification(bill):
            count += 1
    
    logger.info(f"Sent {count} bill reminders for cluster {cluster.name}")
    return count


def send_overdue_notification(bill: Bill) -> bool:
    """Send overdue bill notification."""
    try:
        from accounts.models import AccountUser
        
        recipients = []
        if bill.user_id:
            # User-specific bill
            user = AccountUser.objects.get(id=bill.user_id)
            recipients.append(user)
        else:
            # Cluster-wide bill
            cluster_members = AccountUser.objects.filter(cluster=bill.cluster)
            recipients.extend(cluster_members)

        notifications.send(
            event_name=NotificationEvents.BILL_OVERDUE,
            recipients=recipients,
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "amount": str(bill.amount),
                "due_date": bill.due_date.strftime("%Y-%m-%d") if bill.due_date else "Not set",
                "days_overdue": (timezone.now() - bill.due_date).days if bill.due_date else 0,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send overdue bill notification: {e}")
        return False


def send_reminder_notification(bill: Bill) -> bool:
    """Send bill reminder notification."""
    try:
        from accounts.models import AccountUser
        
        recipients = []
        if bill.user_id:
            # User-specific bill
            user = AccountUser.objects.get(id=bill.user_id)
            recipients.append(user)
        else:
            # Cluster-wide bill
            cluster_members = AccountUser.objects.filter(cluster=bill.cluster)
            recipients.extend(cluster_members)

        notifications.send(
            event_name=NotificationEvents.BILL_REMINDER,
            recipients=recipients,
            cluster=bill.cluster,
            context={
                "bill_number": bill.bill_number,
                "bill_title": bill.title,
                "amount": str(bill.amount),
                "due_date": bill.due_date.strftime("%Y-%m-%d") if bill.due_date else "Not set",
                "days_until_due": (bill.due_date - timezone.now()).days if bill.due_date else 0,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send bill reminder notification: {e}")
        return False