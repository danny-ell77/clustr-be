"""
Recurring payment utilities for ClustR application.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Any
from django.utils import timezone
from django.db import transaction

from core.common.models import (
    RecurringPayment,
    RecurringPaymentStatus,
    RecurringPaymentFrequency,
    Transaction,
    Wallet,
)
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager

logger = logging.getLogger("clustr")


class RecurringPaymentManager:
    """
    Manager for handling recurring payment operations.
    """

    @staticmethod
    def create_recurring_payment(
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
        """
        Create a new recurring payment.

        Args:
            wallet: Wallet to debit
            title: Payment title
            amount: Payment amount
            frequency: Payment frequency
            start_date: Start date for payments
            end_date: Optional end date
            description: Payment description
            metadata: Additional metadata
            created_by: ID of the user creating the payment
            bill: Optional bill to associate with recurring payment
            utility_provider: Optional utility provider for automated payments
            customer_id: Customer ID/meter number for utility payments
            payment_source: Source of payment (wallet or direct)
            spending_limit: Maximum amount per payment

        Returns:
            RecurringPayment: Created recurring payment object
        """
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

        # Send confirmation notification
        RecurringPaymentNotificationManager.send_setup_confirmation(recurring_payment)

        return recurring_payment

    @staticmethod
    def process_due_payments(cluster) -> dict[str, int]:
        """
        Process all due recurring payments for a cluster.

        Args:
            cluster: Cluster object

        Returns:
            Dict: Processing results
        """
        logger.info("Starting automated utility payment processing")

        def _recurring_payment_generator():
            due_payments = (
                RecurringPayment.objects.filter(
                    status=RecurringPaymentStatus.ACTIVE,
                    next_payment_date__lte=timezone.now(),
                )
                .select_related("utility_provider", "wallet", "bill")
                .iterator(batch_size=1000)
            )

            yield due_payments

        total_payments = 0
        successful_payments = 0
        failed_payments = 0

        logger.info(f"Found {total_payments} due  payments")

        for payments in _recurring_payment_generator():
            total_payments += len(payments)
            for payment in payments:
                try:
                    with transaction.atomic():
                        logger.info(
                            f"Processing  payment: {payment.title} - "
                            f"{payment.currency} {payment.amount} for user {payment.user_id}"
                        )

                        success = payment.process_payment()
                        if success:
                            successful_payments += 1
                            logger.info(f" payment {payment.id} processed successfully")
                        else:
                            failed_payments += 1
                            logger.warning(f" payment {payment.id} failed")

                except Exception as e:
                    failed_payments += 1
                    logger.error(f"Error processing  payment {payment.id}: {str(e)}")

        logger.info(
            f" payment processing completed. "
            f"Successful: {successful_payments}, Failed: {failed_payments}"
        )

        return {
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
        }

    @staticmethod
    def pause_recurring_payment(
        payment: RecurringPayment, paused_by: str = None
    ) -> bool:
        """
        Pause a recurring payment.

        Args:
            payment: Recurring payment to pause
            paused_by: ID of the user pausing the payment

        Returns:
            bool: True if paused successfully
        """
        if payment.status != RecurringPaymentStatus.ACTIVE:
            return False

        payment.pause(paused_by)

        logger.info(f"Recurring payment paused: {payment.id}")

        # Send notification
        RecurringPaymentNotificationManager.send_payment_paused_notification(payment)

        return True

    @staticmethod
    def resume_recurring_payment(
        payment: RecurringPayment, resumed_by: str = None
    ) -> bool:
        """
        Resume a paused recurring payment.

        Args:
            payment: Recurring payment to resume
            resumed_by: ID of the user resuming the payment

        Returns:
            bool: True if resumed successfully
        """
        if payment.status != RecurringPaymentStatus.PAUSED:
            return False

        payment.resume(resumed_by)

        logger.info(f"Recurring payment resumed: {payment.id}")

        # Send notification
        RecurringPaymentNotificationManager.send_payment_resumed_notification(payment)

        return True

    @staticmethod
    def cancel_recurring_payment(
        payment: RecurringPayment, cancelled_by: str = None
    ) -> bool:
        """
        Cancel a recurring payment.

        Args:
            payment: Recurring payment to cancel
            cancelled_by: ID of the user cancelling the payment

        Returns:
            bool: True if cancelled successfully
        """
        if payment.status == RecurringPaymentStatus.CANCELLED:
            return False

        payment.cancel(cancelled_by)

        logger.info(f"Recurring payment cancelled: {payment.id}")

        # Send notification
        RecurringPaymentNotificationManager.send_payment_cancelled_notification(payment)

        return True

    @staticmethod
    def get_user_recurring_payments(
        cluster, user_id: str, status: RecurringPaymentStatus = None
    ) -> List[RecurringPayment]:
        """
        Get recurring payments for a user.

        Args:
            cluster: Cluster object
            user_id: User ID
            status: Optional status filter

        Returns:
            List[RecurringPayment]: User's recurring payments
        """
        queryset = RecurringPayment.objects.filter(cluster=cluster, user_id=user_id)

        if status:
            queryset = queryset.filter(status=status)

        return list(queryset)

    @staticmethod
    def get_recurring_payments_summary(cluster, user_id: str) -> dict[str, Any]:
        """
        Get recurring payments summary for a user.

        Args:
            cluster: Cluster object
            user_id: User ID

        Returns:
            Dict: Recurring payments summary
        """
        payments = RecurringPayment.objects.filter(cluster=cluster, user_id=user_id)

        summary = {
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
            "expired_payments": payments.filter(
                status=RecurringPaymentStatus.EXPIRED
            ).count(),
            "total_monthly_amount": sum(
                [
                    p.amount
                    for p in payments.filter(
                        status=RecurringPaymentStatus.ACTIVE,
                        frequency=RecurringPaymentFrequency.MONTHLY,
                    )
                ]
            ),
            "next_payment_date": (
                payments.filter(status=RecurringPaymentStatus.ACTIVE)
                .order_by("next_payment_date")
                .first()
                .next_payment_date
                if payments.filter(status=RecurringPaymentStatus.ACTIVE).exists()
                else None
            ),
        }

        return summary

    @staticmethod
    def send_payment_reminders(cluster, days_before: int = 1) -> int:
        """
        Send reminders for upcoming recurring payments.

        Args:
            cluster: Cluster object
            days_before: Days before payment to send reminder

        Returns:
            int: Number of reminders sent
        """
        reminder_date = timezone.now() + timezone.timedelta(days=days_before)

        payments_to_remind = RecurringPayment.objects.filter(
            cluster=cluster,
            status=RecurringPaymentStatus.ACTIVE,
            next_payment_date__date=reminder_date.date(),
        )

        count = 0
        for payment in payments_to_remind:
            if RecurringPaymentNotificationManager.send_payment_reminder(payment):
                count += 1

        logger.info(f"Sent {count} recurring payment reminders in cluster {cluster.id}")

        return count

    @staticmethod
    def update_payment_schedule(
        payment: RecurringPayment,
        new_amount: Decimal = None,
        new_frequency: RecurringPaymentFrequency = None,
        new_end_date=None,
        updated_by: str = None,
    ) -> bool:
        """
        Update recurring payment schedule.

        Args:
            payment: Recurring payment to update
            new_amount: New payment amount
            new_frequency: New payment frequency
            new_end_date: New end date
            updated_by: ID of the user updating the payment

        Returns:
            bool: True if updated successfully
        """
        if payment.status not in [
            RecurringPaymentStatus.ACTIVE,
            RecurringPaymentStatus.PAUSED,
        ]:
            return False

        changes = {}

        if new_amount and new_amount != payment.amount:
            changes["amount"] = {"old": payment.amount, "new": new_amount}
            payment.amount = new_amount

        if new_frequency and new_frequency != payment.frequency:
            changes["frequency"] = {"old": payment.frequency, "new": new_frequency}
            payment.frequency = new_frequency
            # Recalculate next payment date
            payment.next_payment_date = payment.calculate_next_payment_date()

        if new_end_date != payment.end_date:
            changes["end_date"] = {"old": payment.end_date, "new": new_end_date}
            payment.end_date = new_end_date

        if changes:
            payment.last_modified_by = updated_by
            payment.save()

            logger.info(f"Recurring payment updated: {payment.id}, changes: {changes}")

            # Send notification about changes
            RecurringPaymentNotificationManager.send_payment_updated_notification(
                payment, changes
            )

            return True

        return False

    @staticmethod
    def update_recurring_payment(
        payment: RecurringPayment,
        bill=None,
        title: str = None,
        description: str = None,
        amount: Decimal = None,
        frequency: RecurringPaymentFrequency = None,
        end_date=None,
        utility_provider=None,
        customer_id: str = None,
        spending_limit: Decimal = None,
        metadata: dict = None,
        updated_by: str = None,
    ) -> bool:
        """
        Update a recurring payment with new values.

        Args:
            payment: Recurring payment to update
            bill: New bill to associate
            title: New payment title
            description: New payment description
            amount: New payment amount
            frequency: New payment frequency
            end_date: New end date
            utility_provider: New utility provider
            customer_id: New customer ID
            spending_limit: New spending limit
            metadata: New metadata
            updated_by: ID of the user updating the payment

        Returns:
            bool: True if updated successfully
        """
        if payment.status not in [
            RecurringPaymentStatus.ACTIVE,
            RecurringPaymentStatus.PAUSED,
        ]:
            return False

        changes = {}

        if bill != payment.bill:
            changes["bill"] = {"old": payment.bill_id, "new": bill.id if bill else None}
            payment.bill = bill

        if title and title != payment.title:
            changes["title"] = {"old": payment.title, "new": title}
            payment.title = title

        if description != payment.description:
            changes["description"] = {"old": payment.description, "new": description}
            payment.description = description

        if amount and amount != payment.amount:
            changes["amount"] = {"old": payment.amount, "new": amount}
            payment.amount = amount

        if frequency and frequency != payment.frequency:
            changes["frequency"] = {"old": payment.frequency, "new": frequency}
            payment.frequency = frequency
            # Recalculate next payment date
            payment.next_payment_date = payment.calculate_next_payment_date()

        if end_date != payment.end_date:
            changes["end_date"] = {"old": payment.end_date, "new": end_date}
            payment.end_date = end_date

        if utility_provider != payment.utility_provider:
            changes["utility_provider"] = {
                "old": payment.utility_provider_id,
                "new": utility_provider.id if utility_provider else None,
            }
            payment.utility_provider = utility_provider

        if customer_id != payment.customer_id:
            changes["customer_id"] = {"old": payment.customer_id, "new": customer_id}
            payment.customer_id = customer_id

        if spending_limit != payment.spending_limit:
            changes["spending_limit"] = {
                "old": payment.spending_limit,
                "new": spending_limit,
            }
            payment.spending_limit = spending_limit

        if metadata and metadata != payment.metadata:
            changes["metadata"] = {"old": payment.metadata, "new": metadata}
            payment.metadata = metadata

        if changes:
            payment.last_modified_by = updated_by
            payment.save()

            logger.info(f"Recurring payment updated: {payment.id}, changes: {changes}")

            # Send notification about changes
            RecurringPaymentNotificationManager.send_payment_updated_notification(
                payment, changes
            )

            return True

        return False


class RecurringPaymentNotificationManager:
    """
    Manager for handling recurring payment notifications.
    """

    @staticmethod
    def send_setup_confirmation(payment: RecurringPayment) -> bool:
        """
        Send confirmation when recurring payment is set up.

        Args:
            payment: Recurring payment object

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_SETUP,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "frequency": payment.get_frequency_display(),
                    "start_date": payment.start_date.strftime("%Y-%m-%d"),
                    "end_date": (
                        payment.end_date.strftime("%Y-%m-%d")
                        if payment.end_date
                        else "No end date"
                    ),
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment setup confirmation: {e}")
            return False

    @staticmethod
    def send_payment_reminder(payment: RecurringPayment) -> bool:
        """
        Send reminder for upcoming recurring payment.

        Args:
            payment: Recurring payment object

        Returns:
            bool: True if reminder was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            days_until_payment = (
                payment.next_payment_date.date() - timezone.now().date()
            ).days

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_DUE,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                    "days_until_payment": days_until_payment,
                    "wallet_balance": payment.wallet.available_balance,
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment reminder: {e}")
            return False

    @staticmethod
    def send_payment_processed_notification(
        payment: RecurringPayment, transaction: Transaction
    ) -> bool:
        """
        Send notification when recurring payment is processed.

        Args:
            payment: Recurring payment object
            transaction: Payment transaction

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_CONFIRMED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": transaction.amount,
                    "currency": transaction.currency,
                    "transaction_id": transaction.transaction_id,
                    "payment_date": transaction.processed_at.strftime("%Y-%m-%d %H:%M"),
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                    "wallet_balance": payment.wallet.available_balance,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send recurring payment processed notification: {e}"
            )
            return False

    @staticmethod
    def send_payment_failed_notification(
        payment: RecurringPayment, reason: str
    ) -> bool:
        """
        Send notification when recurring payment fails.

        Args:
            payment: Recurring payment object
            reason: Failure reason

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_FAILED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "failure_reason": reason,
                    "failed_attempts": payment.failed_attempts,
                    "max_attempts": payment.max_failed_attempts,
                    "wallet_balance": payment.wallet.available_balance,
                    "next_retry_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment failed notification: {e}")
            return False

    @staticmethod
    def send_payment_paused_notification(payment: RecurringPayment) -> bool:
        """
        Send notification when recurring payment is paused.

        Args:
            payment: Recurring payment object

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_PAUSED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "failed_attempts": payment.failed_attempts,
                    "wallet_balance": payment.wallet.available_balance,
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment paused notification: {e}")
            return False

    @staticmethod
    def send_payment_resumed_notification(payment: RecurringPayment) -> bool:
        """
        Send notification when recurring payment is resumed.

        Args:
            payment: Recurring payment object

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_RESUMED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                    "wallet_balance": payment.wallet.available_balance,
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment resumed notification: {e}")
            return False

    @staticmethod
    def send_payment_cancelled_notification(payment: RecurringPayment) -> bool:
        """
        Send notification when recurring payment is cancelled.

        Args:
            payment: Recurring payment object

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_CANCELLED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "payment_amount": payment.amount,
                    "currency": payment.currency,
                    "total_payments_made": payment.total_payments,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send recurring payment cancelled notification: {e}"
            )
            return False

    @staticmethod
    def send_payment_updated_notification(
        payment: RecurringPayment, changes: dict
    ) -> bool:
        """
        Send notification when recurring payment is updated.

        Args:
            payment: Recurring payment object
            changes: Dictionary of changes made

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser

            user = AccountUser.objects.filter(id=payment.user_id).first()

            if not user:
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_UPDATED,
                recipients=[user],
                cluster=payment.cluster,
                context={
                    "user_name": user.name,
                    "payment_title": payment.title,
                    "changes": changes,
                    "current_amount": payment.amount,
                    "current_frequency": payment.get_frequency_display(),
                    "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d"),
                },
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send recurring payment updated notification: {e}")
            return False


# Convenience functions for common recurring payment operations
def setup_monthly_service_charge(
    wallet: Wallet, amount: Decimal, created_by: str = None
) -> RecurringPayment:
    """
    Set up monthly service charge recurring payment.

    Args:
        wallet: Wallet to debit
        amount: Monthly service charge amount
        created_by: ID of the user setting up the payment

    Returns:
        RecurringPayment: Created recurring payment
    """
    from dateutil.relativedelta import relativedelta

    start_date = timezone.now().replace(day=1) + relativedelta(
        months=1
    )  # Start next month

    return RecurringPaymentManager.create_recurring_payment(
        wallet=wallet,
        title="Monthly Service Charge",
        amount=amount,
        frequency=RecurringPaymentFrequency.MONTHLY,
        start_date=start_date,
        description="Automated monthly estate service charge payment",
        created_by=created_by,
    )


def setup_utility_autopay(
    wallet: Wallet, utility_type: str, amount: Decimal, created_by: str = None
) -> RecurringPayment:
    """
    Set up utility bill autopay.

    Args:
        wallet: Wallet to debit
        utility_type: Type of utility (electricity, water, etc.)
        amount: Monthly utility amount
        created_by: ID of the user setting up the payment

    Returns:
        RecurringPayment: Created recurring payment
    """
    from dateutil.relativedelta import relativedelta

    start_date = timezone.now() + relativedelta(days=30)  # Start in 30 days

    return RecurringPaymentManager.create_recurring_payment(
        wallet=wallet,
        title=f"{utility_type.title()} Autopay",
        amount=amount,
        frequency=RecurringPaymentFrequency.MONTHLY,
        start_date=start_date,
        description=f"Automated monthly {utility_type.lower()} bill payment",
        metadata={"utility_type": utility_type},
        created_by=created_by,
    )
