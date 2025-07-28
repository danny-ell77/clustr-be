
import logging
from celery import shared_task

from core.common.models import Cluster
from core.common.utils.recurring_payment_utils import RecurringPaymentManager

logger = logging.getLogger(__name__)


@shared_task(name="process_recurring_payments_for_cluster")
def process_recurring_payments_for_cluster(cluster_id):
    """
    Processes due recurring payments for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        results = RecurringPaymentManager.process_due_payments(cluster)
        if results['processed'] > 0 or results['failed'] > 0:
            logger.info(f"Cluster {cluster.name}: Processed {results['processed']}, Failed {results['failed']}, Paused {results['paused']}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(f"Error processing recurring payments for cluster {cluster_id}: {str(e)}")


@shared_task(name="spawn_process_recurring_payments")
def spawn_process_recurring_payments():
    """
    Spawns a task to process recurring payments for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        process_recurring_payments_for_cluster.delay(cluster.id)


@shared_task(name="send_recurring_payment_reminders_for_cluster")
def send_recurring_payment_reminders_for_cluster(cluster_id):
    """
    Sends reminders for upcoming recurring payments for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        reminders_sent = RecurringPaymentManager.send_payment_reminders(cluster, days_before=1)
        if reminders_sent > 0:
            logger.info(f"Sent {reminders_sent} recurring payment reminders for cluster {cluster.name}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(f"Error sending recurring payment reminders for cluster {cluster_id}: {str(e)}")


@shared_task(name="spawn_send_recurring_payment_reminders")
def spawn_send_recurring_payment_reminders():
    """
    Spawns a task to send recurring payment reminders for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        send_recurring_payment_reminders_for_cluster.delay(cluster.id)
