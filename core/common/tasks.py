import logging
from typing import Iterable

from celery import shared_task
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    ignore_result=True,  # We have no need for the result
    name="send_account_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    serializer="pickle",
)
def send_account_email(email_messages: Iterable[EmailMessage]):
    # TODO: Add a callback with the email content as an argument of type SentEmailContent
    fail_silently = not settings.DEBUG
    with mail.get_connection(fail_silently=fail_silently) as connection:
        connection.send_messages(email_messages)


@shared_task(
    ignore_result=True,
    name="retry_failed_utility_payments",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def retry_failed_utility_payments():
    """
    Celery task to retry failed utility payments that can be retried.
    """
    from core.common.models.wallet import PaymentError, TransactionStatus
    from django.db import transaction

    logger.info("Starting retry of failed utility payments")

    # Get retryable payment errors
    retryable_errors = PaymentError.objects.filter(
        is_resolved=False,
        can_retry=True,
        retry_count__lt=3,  # Max 3 retries
        transaction__type="bill_payment",
        transaction__status=TransactionStatus.FAILED,
        transaction__metadata__utility_provider_id__isnull=False,
    ).select_related("transaction", "transaction__wallet")

    total_retries = retryable_errors.count()
    successful_retries = 0
    failed_retries = 0

    logger.info(f"Found {total_retries} retryable utility payment errors")

    for error in retryable_errors:
        try:
            with transaction.atomic():
                # Check if enough time has passed for retry
                from datetime import timedelta

                retry_delay = error.get_next_retry_delay()
                if error.created_at + timedelta(minutes=retry_delay) > timezone.now():
                    continue

                logger.info(f"Retrying utility payment error {error.id}")

                # Increment retry count
                error.increment_retry_count()

                # Attempt to recreate and process the payment
                transaction_data = error.transaction
                utility_provider_id = transaction_data.metadata.get(
                    "utility_provider_id"
                )
                customer_id = transaction_data.metadata.get("customer_id")

                if utility_provider_id and customer_id:
                    from core.common.models.wallet import UtilityProvider
                    from core.common.services.utility_service import (
                        UtilityPaymentManager,
                    )

                    try:
                        utility_provider = UtilityProvider.objects.get(
                            id=utility_provider_id
                        )

                        result = UtilityPaymentManager.process_utility_payment(
                            user_id=transaction_data.wallet.user_id,
                            utility_provider=utility_provider,
                            customer_id=customer_id,
                            amount=transaction_data.amount,
                            wallet=transaction_data.wallet,
                            description=f"Retry: {transaction_data.description}",
                        )

                        if result.get("success"):
                            error.mark_as_resolved("automatic_retry")
                            successful_retries += 1
                            logger.info(f"Utility payment retry {error.id} successful")
                        else:
                            failed_retries += 1
                            logger.warning(
                                f"Utility payment retry {error.id} failed: {result.get('error')}"
                            )

                    except UtilityProvider.DoesNotExist:
                        logger.error(
                            f"Utility provider {utility_provider_id} not found for retry"
                        )
                        failed_retries += 1

        except Exception as e:
            failed_retries += 1
            logger.error(f"Error retrying utility payment {error.id}: {str(e)}")

    logger.info(
        f"Utility payment retry completed. "
        f"Successful: {successful_retries}, Failed: {failed_retries}"
    )

    return {
        "total_retries": total_retries,
        "successful_retries": successful_retries,
        "failed_retries": failed_retries,
    }
