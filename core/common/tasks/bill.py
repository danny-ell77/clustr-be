
import logging
from celery import shared_task

from core.common.models import Cluster
from core.common.utils.bill_utils import BillManager

logger = logging.getLogger(__name__)


@shared_task(name="check_overdue_bills_for_cluster")
def check_overdue_bills_for_cluster(cluster_id):
    """
    Checks for overdue bills for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        overdue_count = BillManager.check_and_update_overdue_bills(cluster)
        if overdue_count > 0:
            logger.info(f"Marked {overdue_count} bills as overdue for cluster {cluster.name}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(f"Error checking overdue bills for cluster {cluster_id}: {str(e)}")


@shared_task(name="spawn_check_overdue_bills")
def spawn_check_overdue_bills():
    """
    Spawns a task to check overdue bills for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        check_overdue_bills_for_cluster.delay(cluster.id)


@shared_task(name="send_bill_reminders_for_cluster")
def send_bill_reminders_for_cluster(cluster_id):
    """
    Sends reminders for bills approaching due date for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        reminders_sent = BillManager.send_bill_reminders(cluster, days_before_due=3)
        if reminders_sent > 0:
            logger.info(f"Sent {reminders_sent} bill reminders for cluster {cluster.name}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(f"Error sending bill reminders for cluster {cluster_id}: {str(e)}")


@shared_task(name="spawn_send_bill_reminders")
def spawn_send_bill_reminders():
    """
    Spawns a task to send bill reminders for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        send_bill_reminders_for_cluster.delay(cluster.id)
