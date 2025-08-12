
import logging
from celery import shared_task

from core.common.models import Cluster
from core.common.includes import maintenance

logger = logging.getLogger(__name__)


@shared_task(name="process_maintenance_schedules_for_cluster")
def process_maintenance_schedules_for_cluster(cluster_id):
    """
    Processes due maintenance schedules for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        created_logs = maintenance.process_due_schedules(cluster)
        if created_logs:
            logger.info(f"Created {len(created_logs)} maintenance logs for cluster {cluster.name}")
        
        alerts_sent = maintenance.send_due_alerts(cluster)
        if alerts_sent:
            logger.info(f"Sent {alerts_sent} maintenance due alerts for cluster {cluster.name}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(f"Error processing maintenance schedules for cluster {cluster_id}: {str(e)}")


@shared_task(name="spawn_process_maintenance_schedules")
def spawn_process_maintenance_schedules():
    """
    Spawns a task to process maintenance schedules for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        process_maintenance_schedules_for_cluster.delay(cluster.id)
