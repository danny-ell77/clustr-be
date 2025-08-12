import logging
from celery import shared_task

from core.common.models import Cluster
from core.common.includes import tasks
from core.notifications import notifications
from core.notifications.events import NotificationEvents

logger = logging.getLogger(__name__)


@shared_task(name="check_task_deadlines_for_cluster")
def check_task_deadlines_for_cluster(cluster_id):
    """
    Checks task deadlines for a specific cluster.
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        overdue_tasks = tasks.get_overdue(cluster)
        due_soon_tasks = tasks.get_due_soon(cluster)
        if overdue_tasks.iterator(chunk_size=1000):
            for task in overdue_tasks:
                tasks.escalate(
                    task, task.created_by, "Task is overdue", task.created_by
                )
        if due_soon_tasks.iterator(chunk_size=1000):
            for task in due_soon_tasks:
                notifications.send(
                    NotificationEvents.TASK_DUE,
                    [task.created_by],
                    cluster,
                    {"task": task},
                )
        logger.info(f"Completed task deadline checks for cluster: {cluster.name}")
    except Cluster.DoesNotExist:
        logger.error(f"Cluster with id {cluster_id} not found.")
    except Exception as e:
        logger.error(
            f"Error checking task deadlines for cluster {cluster_id}: {str(e)}"
        )


@shared_task(name="spawn_check_task_deadlines")
def spawn_check_task_deadlines():
    """
    Spawns a task to check deadlines for each cluster.
    """
    for cluster in Cluster.objects.all().iterator():
        check_task_deadlines_for_cluster.delay(cluster.id)
