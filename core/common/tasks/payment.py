import logging
from celery import shared_task
from django.utils import timezone

from core.common.models import Cluster
from core.common.includes import recurring_payments

logger = logging.getLogger(__name__)


@shared_task(name="process_recurring_payments_for_cluster")
def process_recurring_payments_for_cluster(cluster_id):
    """
    Processes due recurring payments for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        results = recurring_payments.process_due_payments(cluster)
        if results["processed"] > 0 or results["failed"] > 0:
            logger.info(
                f"Cluster {cluster.name}: Processed {results['processed']}, Failed {results['failed']}, Paused {results['paused']}"
            )
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(
            f"Error processing recurring payments for cluster {cluster_id}: {str(e)}"
        )


@shared_task(name="spawn_process_recurring_payments")
def spawn_process_recurring_payments():
    """
    Spawns a task to process recurring payments for each cluster.
    """
    for cluster in Cluster.objects.all().iterator(chunk_size=1000):
        process_recurring_payments_for_cluster.delay(cluster.id)


@shared_task(name="send_recurring_payment_reminders_for_cluster")
def send_recurring_payment_reminders_for_cluster(cluster_id):
    """
    Sends reminders for upcoming recurring payments for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        reminders_sent = recurring_payments.send_payment_reminders(
            cluster, days_before=1
        )
        if reminders_sent > 0:
            logger.info(
                f"Sent {reminders_sent} recurring payment reminders for cluster {cluster.name}"
            )
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(
            f"Error sending recurring payment reminders for cluster {cluster_id}: {str(e)}"
        )


@shared_task(name="spawn_send_recurring_payment_reminders")
def spawn_send_recurring_payment_reminders():
    """
    Spawns a task to send recurring payment reminders for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        send_recurring_payment_reminders_for_cluster.delay(cluster.id)


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
    from core.common.models import PaymentError, TransactionStatus
    from django.db import transaction

    logger.info("Starting retry of failed utility payments")

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
                    from core.common.models import UtilityProvider
                    from core.common.includes import payments

                    try:
                        utility_provider = UtilityProvider.objects.get(
                            id=utility_provider_id
                        )

                        from core.common.includes import utilities
                        result = utilities.process_utility_payment(
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