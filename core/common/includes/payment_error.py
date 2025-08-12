"""
Payment error handling utilities for ClustR application.
"""

import logging
from enum import Enum
from typing import Any
from django.utils import timezone

from core.common.models import (
    Transaction,
    TransactionStatus,
    PaymentProvider,
    RecurringPayment,
    RecurringPaymentStatus,
)
from core.common.error_utils import log_exceptions
from core.common.models import PaymentError
from core.common.includes.third_party_services import PaymentProviderFactory

logger = logging.getLogger("clustr")


class PaymentErrorType(Enum):
    """Types of payment errors."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_CARD = "invalid_card"
    EXPIRED_CARD = "expired_card"
    DECLINED_CARD = "declined_card"
    NETWORK_ERROR = "network_error"
    PROVIDER_ERROR = "provider_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    LIMIT_EXCEEDED = "limit_exceeded"
    ACCOUNT_SUSPENDED = "account_suspended"
    UNKNOWN_ERROR = "unknown_error"


class PaymentErrorSeverity(Enum):
    """Severity levels for payment errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PAYSTACK_ERROR_MAPPING = {
    "insufficient_funds": PaymentErrorType.INSUFFICIENT_FUNDS,
    "invalid_card": PaymentErrorType.INVALID_CARD,
    "expired_card": PaymentErrorType.EXPIRED_CARD,
    "declined": PaymentErrorType.DECLINED_CARD,
    "timeout": PaymentErrorType.TIMEOUT_ERROR,
}

FLUTTERWAVE_ERROR_MAPPING = {
    "insufficient_funds": PaymentErrorType.INSUFFICIENT_FUNDS,
    "invalid_card": PaymentErrorType.INVALID_CARD,
    "expired_card": PaymentErrorType.EXPIRED_CARD,
    "declined": PaymentErrorType.DECLINED_CARD,
    "network_error": PaymentErrorType.NETWORK_ERROR,
}


def categorize_error(error_message: str, provider: PaymentProvider) -> PaymentErrorType:
    """
    Categorize payment error based on error message and provider.

    Args:
        error_message: Error message from payment provider
        provider: Payment provider

    Returns:
        PaymentErrorType: Categorized error type
    """
    error_message_lower = error_message.lower()

    # Common error patterns
    if any(
        keyword in error_message_lower
        for keyword in ["insufficient", "balance", "funds"]
    ):
        return PaymentErrorType.INSUFFICIENT_FUNDS
    elif any(keyword in error_message_lower for keyword in ["invalid", "card"]):
        return PaymentErrorType.INVALID_CARD
    elif any(keyword in error_message_lower for keyword in ["expired", "expiry"]):
        return PaymentErrorType.EXPIRED_CARD
    elif any(keyword in error_message_lower for keyword in ["declined", "rejected"]):
        return PaymentErrorType.DECLINED_CARD
    elif any(
        keyword in error_message_lower
        for keyword in ["network", "connection", "timeout"]
    ):
        return PaymentErrorType.NETWORK_ERROR
    elif any(
        keyword in error_message_lower for keyword in ["authentication", "unauthorized"]
    ):
        return PaymentErrorType.AUTHENTICATION_ERROR
    elif any(keyword in error_message_lower for keyword in ["limit", "exceeded"]):
        return PaymentErrorType.LIMIT_EXCEEDED
    elif any(keyword in error_message_lower for keyword in ["suspended", "blocked"]):
        return PaymentErrorType.ACCOUNT_SUSPENDED
    else:
        return PaymentErrorType.UNKNOWN_ERROR


def get_error_severity(error_type: PaymentErrorType) -> PaymentErrorSeverity:
    """
    Get severity level for error type.

    Args:
        error_type: Payment error type

    Returns:
        PaymentErrorSeverity: Error severity level
    """
    severity_mapping = {
        PaymentErrorType.INSUFFICIENT_FUNDS: PaymentErrorSeverity.MEDIUM,
        PaymentErrorType.INVALID_CARD: PaymentErrorSeverity.HIGH,
        PaymentErrorType.EXPIRED_CARD: PaymentErrorSeverity.MEDIUM,
        PaymentErrorType.DECLINED_CARD: PaymentErrorSeverity.MEDIUM,
        PaymentErrorType.NETWORK_ERROR: PaymentErrorSeverity.LOW,
        PaymentErrorType.PROVIDER_ERROR: PaymentErrorSeverity.HIGH,
        PaymentErrorType.VALIDATION_ERROR: PaymentErrorSeverity.MEDIUM,
        PaymentErrorType.TIMEOUT_ERROR: PaymentErrorSeverity.LOW,
        PaymentErrorType.AUTHENTICATION_ERROR: PaymentErrorSeverity.HIGH,
        PaymentErrorType.LIMIT_EXCEEDED: PaymentErrorSeverity.MEDIUM,
        PaymentErrorType.ACCOUNT_SUSPENDED: PaymentErrorSeverity.CRITICAL,
        PaymentErrorType.UNKNOWN_ERROR: PaymentErrorSeverity.MEDIUM,
    }

    return severity_mapping.get(error_type, PaymentErrorSeverity.MEDIUM)


def get_user_friendly_message(error_type: PaymentErrorType) -> str:
    """
    Get user-friendly error message.

    Args:
        error_type: Payment error type

    Returns:
        str: User-friendly error message
    """
    messages = {
        PaymentErrorType.INSUFFICIENT_FUNDS: "You don't have enough funds in your account to complete this transaction.",
        PaymentErrorType.INVALID_CARD: "The card information provided is invalid. Please check your card details and try again.",
        PaymentErrorType.EXPIRED_CARD: "Your card has expired. Please use a different card or update your card information.",
        PaymentErrorType.DECLINED_CARD: "Your card was declined by your bank. Please contact your bank or try a different card.",
        PaymentErrorType.NETWORK_ERROR: "There was a network error while processing your payment. Please try again.",
        PaymentErrorType.PROVIDER_ERROR: "There was an error with the payment service. Please try again later.",
        PaymentErrorType.VALIDATION_ERROR: "The payment information provided is invalid. Please check and try again.",
        PaymentErrorType.TIMEOUT_ERROR: "The payment request timed out. Please try again.",
        PaymentErrorType.AUTHENTICATION_ERROR: "There was an authentication error. Please verify your account and try again.",
        PaymentErrorType.LIMIT_EXCEEDED: "You have exceeded your transaction limit. Please try a smaller amount or contact support.",
        PaymentErrorType.ACCOUNT_SUSPENDED: "Your account has been suspended. Please contact support for assistance.",
        PaymentErrorType.UNKNOWN_ERROR: "An unexpected error occurred while processing your payment. Please try again or contact support.",
    }

    return messages.get(error_type, "An error occurred while processing your payment.")


def get_recovery_options(
    error_type: PaymentErrorType, transaction: Transaction
) -> dict[str, Any]:
    """
    Get recovery options for payment error.

    Args:
        error_type: Payment error type
        transaction: Failed transaction

    Returns:
        Dict: Recovery options
    """
    base_options = {
        "can_retry": True,
        "retry_delay_minutes": 5,
        "max_retries": 3,
        "alternative_methods": [],
        "support_contact": "support@clustr.app",
        "support_phone": "+234-800-CLUSTR",
    }

    # Customize options based on error type
    if error_type == PaymentErrorType.INSUFFICIENT_FUNDS:
        base_options.update(
            {
                "can_retry": False,
                "suggested_actions": [
                    "Add funds to your wallet",
                    "Use a different payment method",
                    "Try a smaller amount",
                ],
                "alternative_methods": ["bank_transfer", "cash_deposit"],
            }
        )

    elif error_type == PaymentErrorType.INVALID_CARD:
        base_options.update(
            {
                "can_retry": True,
                "suggested_actions": [
                    "Check your card number",
                    "Verify expiry date and CVV",
                    "Try a different card",
                ],
                "alternative_methods": ["bank_transfer", "different_card"],
            }
        )

    elif error_type == PaymentErrorType.EXPIRED_CARD:
        base_options.update(
            {
                "can_retry": False,
                "suggested_actions": [
                    "Use a different card",
                    "Update your card information",
                ],
                "alternative_methods": ["bank_transfer", "different_card"],
            }
        )

    elif error_type == PaymentErrorType.DECLINED_CARD:
        base_options.update(
            {
                "can_retry": True,
                "max_retries": 1,
                "suggested_actions": [
                    "Contact your bank",
                    "Try a different card",
                    "Use bank transfer",
                ],
                "alternative_methods": ["bank_transfer", "different_card"],
            }
        )

    elif error_type == PaymentErrorType.NETWORK_ERROR:
        base_options.update(
            {
                "can_retry": True,
                "retry_delay_minutes": 2,
                "max_retries": 5,
                "suggested_actions": [
                    "Check your internet connection",
                    "Try again in a few minutes",
                ],
            }
        )

    elif error_type == PaymentErrorType.ACCOUNT_SUSPENDED:
        base_options.update(
            {
                "can_retry": False,
                "suggested_actions": [
                    "Contact support immediately",
                    "Verify your account status",
                ],
                "alternative_methods": [],
            }
        )

    # Add provider-specific alternatives
    if transaction.provider == PaymentProvider.PAYSTACK:
        base_options["alternative_methods"].append("flutterwave")
    elif transaction.provider == PaymentProvider.FLUTTERWAVE:
        base_options["alternative_methods"].append("paystack")

    return base_options


@log_exceptions(log_level=logging.ERROR)
def handle_transaction_failure(
    transaction: Transaction, error_message: str
) -> dict[str, Any]:
    """
    Handle transaction failure and provide recovery options.

    Args:
        transaction: Failed transaction
        error_message: Error message from payment provider

    Returns:
        Dict: Error handling result with recovery options
    """
    # Categorize the error
    error_type = categorize_error(error_message, transaction.provider)
    severity = get_error_severity(error_type)
    user_message = get_user_friendly_message(error_type)
    recovery_options = get_recovery_options(error_type, transaction)

    # Update transaction with error details
    transaction.mark_as_failed(error_message)

    # Log the error
    logger.error(
        f"Payment transaction failed: {transaction.transaction_id}",
        extra={
            "transaction_id": transaction.transaction_id,
            "error_type": error_type.value,
            "severity": severity.value,
            "provider": transaction.provider,
            "amount": str(transaction.amount),
            "user_id": str(transaction.wallet.user_id),
            "cluster_id": str(transaction.cluster.id),
        },
    )

    # Send error notification to user
    send_payment_failed_notification(
        transaction, error_type, user_message, recovery_options
    )

    # Handle critical errors
    if severity == PaymentErrorSeverity.CRITICAL:
        _handle_critical_error(transaction, error_type)

    return {
        "error_type": error_type.value,
        "severity": severity.value,
        "user_message": user_message,
        "recovery_options": recovery_options,
        "transaction_id": transaction.transaction_id,
    }


def handle_recurring_payment_failure(
    recurring_payment: RecurringPayment, error_message: str
) -> dict[str, Any]:
    """
    Handle recurring payment failure.

    Args:
        recurring_payment: Failed recurring payment
        error_message: Error message

    Returns:
        Dict: Error handling result
    """
    error_type = categorize_error(error_message, PaymentProvider.CASH)
    severity = get_error_severity(error_type)

    # Increment failed attempts
    recurring_payment.failed_attempts += 1

    # Pause if max attempts reached
    if recurring_payment.failed_attempts >= recurring_payment.max_failed_attempts:
        recurring_payment.status = RecurringPaymentStatus.PAUSED
        logger.warning(
            f"Recurring payment paused due to failures: {recurring_payment.id}"
        )

    recurring_payment.save()

    # Send notification
    send_recurring_payment_failed_notification(
        recurring_payment, error_type, error_message
    )

    return {
        "error_type": error_type.value,
        "severity": severity.value,
        "failed_attempts": recurring_payment.failed_attempts,
        "status": recurring_payment.status,
        "paused": recurring_payment.status == RecurringPaymentStatus.PAUSED,
    }


def _handle_critical_error(transaction: Transaction, error_type: PaymentErrorType):
    """
    Handle critical payment errors.

    Args:
        transaction: Failed transaction
        error_type: Error type
    """
    # Notify administrators for critical errors
    if error_type == PaymentErrorType.ACCOUNT_SUSPENDED:
        send_admin_alert(transaction, error_type)

    # Additional critical error handling can be added here
    pass


def retry_failed_transaction(transaction: Transaction) -> bool:
    """
    Retry a failed transaction.

    Args:
        transaction: Failed transaction to retry

    Returns:
        bool: True if retry was initiated successfully
    """
    if transaction.status != TransactionStatus.FAILED:
        return False

    # Check if transaction can be retried
    retry_count = (
        transaction.metadata.get("retry_count", 0) if transaction.metadata else 0
    )

    if retry_count >= 3:  # Max 3 retries
        logger.warning(f"Transaction {transaction.transaction_id} exceeded max retries")
        return False

    # Update retry count
    if not transaction.metadata:
        transaction.metadata = {}
    transaction.metadata["retry_count"] = retry_count + 1
    transaction.metadata["last_retry_at"] = timezone.now().isoformat()

    # Reset transaction status
    transaction.status = TransactionStatus.PENDING
    transaction.failed_at = None
    transaction.failure_reason = None
    transaction.save()

    logger.info(
        f"Retrying transaction {transaction.transaction_id} (attempt {retry_count + 1})"
    )

    return True


def send_payment_failed_notification(
    transaction: Transaction,
    error_type: PaymentErrorType,
    user_message: str,
    recovery_options: dict,
) -> bool:
    """
    Send payment failure notification to user.

    Args:
        transaction: Failed transaction
        error_type: Error type
        user_message: User-friendly error message
        recovery_options: Recovery options

    Returns:
        bool: True if notification was sent successfully
    """
    try:
        from accounts.models import AccountUser
        from core.common.includes import notifications
        from core.notifications.events import NotificationEvents

        user = AccountUser.objects.filter(id=transaction.wallet.user_id).first()

        if not user:
            return False

        return notifications.send(
            event=NotificationEvents.PAYMENT_FAILED,
            recipients=[user],
            cluster=transaction.cluster,
            context={
                "user_name": user.name,
                "transaction_id": transaction.transaction_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "error_message": user_message,
                "error_type": error_type.value,
                "can_retry": recovery_options.get("can_retry", False),
                "suggested_actions": recovery_options.get("suggested_actions", []),
                "alternative_methods": recovery_options.get("alternative_methods", []),
                "support_contact": recovery_options.get("support_contact", ""),
                "support_phone": recovery_options.get("support_phone", ""),
            },
        )

    except Exception as e:
        logger.error(f"Failed to send payment failed notification: {e}")
        return False


def send_recurring_payment_failed_notification(
    recurring_payment: RecurringPayment,
    error_type: PaymentErrorType,
    error_message: str,
) -> bool:
    """
    Send recurring payment failure notification.

    Args:
        recurring_payment: Failed recurring payment
        error_type: Error type
        error_message: Error message

    Returns:
        bool: True if notification was sent successfully
    """
    try:
        from accounts.models import AccountUser
        from core.common.includes import notifications
        from core.notifications.events import NotificationEvents

        user = AccountUser.objects.filter(id=recurring_payment.user_id).first()

        if not user:
            return False

        return notifications.send(
            event=NotificationEvents.PAYMENT_FAILED,
            recipients=[user],
            cluster=recurring_payment.cluster,
            context={
                "user_name": user.name,
                "payment_title": recurring_payment.title,
                "amount": recurring_payment.amount,
                "currency": recurring_payment.currency,
                "error_message": get_user_friendly_message(error_type),
                "failed_attempts": recurring_payment.failed_attempts,
                "max_attempts": recurring_payment.max_failed_attempts,
                "is_paused": recurring_payment.status == RecurringPaymentStatus.PAUSED,
                "next_retry_date": recurring_payment.next_payment_date.strftime(
                    "%Y-%m-%d"
                ),
            },
        )

    except Exception as e:
        logger.error(f"Failed to send recurring payment failed notification: {e}")
        return False


def send_admin_alert(transaction: Transaction, error_type: PaymentErrorType) -> bool:
    """
    Send alert to administrators for critical payment errors.

    Args:
        transaction: Failed transaction
        error_type: Error type

    Returns:
        bool: True if alert was sent successfully
    """
    try:
        from accounts.models import AccountUser
        from core.common.includes import notifications
        from core.notifications.events import NotificationEvents

        # Get cluster administrators
        admins = AccountUser.objects.filter(
            clusters=transaction.cluster, is_cluster_admin=True
        )

        if not admins.exists():
            logger.warning(
                f"No administrators found for cluster {transaction.cluster.name}"
            )
            return False

        return notifications.send(
            event=NotificationEvents.PAYMENT_FAILED,
            recipients=list(admins),
            cluster=transaction.cluster,
            context={
                "transaction_id": transaction.transaction_id,
                "user_id": str(transaction.wallet.user_id),
                "amount": transaction.amount,
                "currency": transaction.currency,
                "error_type": error_type.value,
                "error_message": transaction.failure_reason
                or get_user_friendly_message(error_type),
                "cluster_name": transaction.cluster.name,
                "timestamp": (
                    transaction.failed_at.strftime("%Y-%m-%d %H:%M:%S")
                    if transaction.failed_at
                    else timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                ),
                "is_admin_alert": True,
            },
        )

    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
        return False


# Convenience functions for error handling
def handle_payment_error(
    transaction: Transaction, error_message: str
) -> dict[str, Any]:
    return handle_transaction_failure(transaction, error_message)


def create_payment_error_record(
    transaction: Transaction, error_message: str, provider_error_code: str = None
) -> PaymentError:

    # Categorize the error
    error_type = categorize_error(error_message, transaction.provider)
    severity = get_error_severity(error_type)
    user_message = get_user_friendly_message(error_type)
    recovery_options = get_recovery_options(error_type, transaction)

    # Create PaymentError record
    payment_error = PaymentError.objects.create(
        cluster=transaction.cluster,
        transaction=transaction,
        error_type=error_type,
        severity=severity,
        provider_error_code=provider_error_code,
        provider_error_message=error_message,
        user_friendly_message=user_message,
        recovery_options=recovery_options,
        can_retry=recovery_options.get("can_retry", True),
        max_retries=recovery_options.get("max_retries", 3),
        created_by=transaction.created_by,
        last_modified_by=transaction.last_modified_by,
    )

    # Send notifications
    send_payment_failed_notification(
        transaction, error_type, user_message, recovery_options
    )

    # Mark notification flags
    payment_error.user_notified = True
    if severity == PaymentErrorSeverity.CRITICAL:
        send_admin_alert(transaction, error_type)
        payment_error.admin_notified = True

    payment_error.save()

    return payment_error


def retry_failed_payment(payment_error: PaymentError) -> tuple[bool, str]:

    if not payment_error.can_be_retried():
        return False, "Payment cannot be retried"

    transaction = payment_error.transaction

    try:
        # Get payment provider
        provider = PaymentProviderFactory.get_provider(transaction.provider)

        # Increment retry count
        payment_error.increment_retry_count()

        # Reset transaction status
        transaction.status = TransactionStatus.PENDING
        transaction.failed_at = None
        transaction.failure_reason = None
        transaction.save()

        # For deposit transactions, re-initialize payment
        if transaction.type == "deposit":
            # This would need user email and callback URL from metadata
            metadata = transaction.metadata or {}
            email = metadata.get("user_email", "")
            callback_url = metadata.get("callback_url", "")

            if email and callback_url:
                result = provider.initialize_payment(
                    amount=transaction.amount,
                    currency=transaction.currency,
                    email=email,
                    callback_url=callback_url,
                    metadata=metadata,
                )

                # Update transaction with new reference
                transaction.reference = result["reference"]
                transaction.provider_response = result
                transaction.save()

                return (
                    True,
                    f"Payment retry initiated. Reference: {result['reference']}",
                )

        return True, "Payment retry initiated successfully"

    except Exception as e:
        logger.error(f"Failed to retry payment {payment_error.id}: {e}")
        transaction.mark_as_failed(f"Retry failed: {str(e)}")
        return False, f"Retry failed: {str(e)}"
