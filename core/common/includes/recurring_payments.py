"""
Recurring payments utilities for ClustR application.
Refactored from RecurringPaymentManager static methods to pure functions.
"""

import logging
from decimal import Decimal
from typing import Any, Optional


from core.common.models import (
    RecurringPayment,
    RecurringPaymentFrequency,
    RecurringPaymentStatus,
    Wallet,
)

logger = logging.getLogger("clustr")


def create(
    wallet: Wallet,
    title: str,
    amount: Decimal,
    frequency: RecurringPaymentFrequency,
    start_date,
    end_date=None,
    description: str = None,
    metadata: Optional[dict] = None,
    created_by: str = None,
    bill=None,
    utility_provider=None,
    customer_id: str = None,
    payment_source: str = "wallet",
    spending_limit: Decimal = None,
) -> RecurringPayment:
    """Create a new recurring payment."""
    recurring_payment = RecurringPayment.objects.create(
        cluster=wallet.cluster,
        user_id=wallet.user_id,
        wallet=wallet,
        bill=bill,
        title=title,
        description=description,
        amount=amount,
        currency=wallet.currency,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        next_payment_date=start_date,
        utility_provider=utility_provider,
        customer_id=customer_id,
        payment_source=payment_source,
        spending_limit=spending_limit,
        metadata=metadata or {},
        created_by=created_by,
        last_modified_by=created_by,
    )

    logger.info(
        f"Recurring payment created: {recurring_payment.id} for user {wallet.user_id}"
    )
    return recurring_payment


def pause(payment: RecurringPayment, paused_by: str = None) -> bool:
    """Pause a recurring payment."""
    if payment.status != RecurringPaymentStatus.ACTIVE:
        return False

    payment.pause(paused_by)
    logger.info(f"Recurring payment paused: {payment.id}")
    return True


def resume(payment: RecurringPayment, resumed_by: str = None) -> bool:
    """Resume a paused recurring payment."""
    if payment.status != RecurringPaymentStatus.PAUSED:
        return False

    payment.resume(resumed_by)
    logger.info(f"Recurring payment resumed: {payment.id}")
    return True


def cancel(payment: RecurringPayment, cancelled_by: str = None) -> bool:
    """Cancel a recurring payment."""
    if payment.status == RecurringPaymentStatus.CANCELLED:
        return False

    payment.cancel(cancelled_by)
    logger.info(f"Recurring payment cancelled: {payment.id}")
    return True


def update(payment: RecurringPayment, **kwargs) -> bool:
    """Update a recurring payment."""
    try:
        for key, value in kwargs.items():
            if hasattr(payment, key) and value is not None:
                setattr(payment, key, value)

        payment.save()
        logger.info(f"Recurring payment updated: {payment.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update recurring payment {payment.id}: {e}")
        return False


def get_summary(cluster, user_id: str) -> dict[str, Any]:
    """Get recurring payments summary for a user."""
    payments = RecurringPayment.objects.filter(cluster=cluster, user_id=user_id)

    return {
        "total_payments": payments.count(),
        "active_payments": payments.filter(
            status=RecurringPaymentStatus.ACTIVE
        ).count(),
        "paused_payments": payments.filter(
            status=RecurringPaymentStatus.PAUSED
        ).count(),
        "cancelled_payments": payments.filter(
            status=RecurringPaymentStatus.CANCELLED
        ).count(),
    }

def process_due_payments(cluster) -> dict[str, int]:
    """
    Process due recurring payments for a cluster.
    
    Args:
        cluster: Cluster to process payments for
        
    Returns:
        Dictionary with counts of processed, failed, and paused payments
    """
    from django.utils import timezone
    from core.common.includes import payments
    
    now = timezone.now()
    due_payments = RecurringPayment.objects.filter(
        cluster=cluster,
        status=RecurringPaymentStatus.ACTIVE,
        next_payment_date__lte=now
    )
    
    results = {"processed": 0, "failed": 0, "paused": 0}
    
    for payment in due_payments:
        try:
            # Check if wallet has sufficient balance
            if not payment.wallet.has_sufficient_balance(payment.amount):
                logger.warning(f"Insufficient balance for recurring payment {payment.id}")
                results["failed"] += 1
                continue
            
            # Process the payment
            transaction = payments.process_recurring_payment(payment)
            if transaction:
                payment.update_next_payment_date()
                results["processed"] += 1
                logger.info(f"Processed recurring payment {payment.id}")
            else:
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"Failed to process recurring payment {payment.id}: {e}")
            results["failed"] += 1
    
    return results


def send_payment_reminders(cluster, days_before: int = 1) -> int:
    """
    Send reminders for upcoming recurring payments.
    
    Args:
        cluster: Cluster to send reminders for
        days_before: Number of days before payment to send reminder
        
    Returns:
        Number of reminders sent
    """
    from django.utils import timezone
    from datetime import timedelta
    from core.common.includes import notifications
    from core.notifications.events import NotificationEvents
    from accounts.models import AccountUser
    
    now = timezone.now()
    reminder_date = now + timedelta(days=days_before)
    
    upcoming_payments = RecurringPayment.objects.filter(
        cluster=cluster,
        status=RecurringPaymentStatus.ACTIVE,
        next_payment_date__gte=now,
        next_payment_date__lte=reminder_date
    )
    
    count = 0
    for payment in upcoming_payments:
        try:
            user = AccountUser.objects.get(id=payment.user_id)
            
            notifications.send(
                event_name=NotificationEvents.RECURRING_PAYMENT_REMINDER,
                recipients=[user],
                cluster=cluster,
                context={
                    "payment_title": payment.title,
                    "amount": str(payment.amount),
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                    "frequency": payment.get_frequency_display(),
                },
            )
            count += 1
            
        except Exception as e:
            logger.error(f"Failed to send recurring payment reminder for {payment.id}: {e}")
    
    logger.info(f"Sent {count} recurring payment reminders for cluster {cluster.name}")
    return count