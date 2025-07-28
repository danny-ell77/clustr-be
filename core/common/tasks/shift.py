
import logging
from celery import shared_task

from core.common.utils.shift_utils import ShiftManager

logger = logging.getLogger(__name__)


@shared_task(name="check_missed_shifts")
def check_missed_shifts():
    """
    Checks for missed shifts and marks them as no-show.
    This task should be called periodically by a scheduler.
    """
    try:
        ShiftManager.mark_missed_shifts()
        logger.info("Completed missed shifts check")
    except Exception as e:
        logger.error(f"Error checking missed shifts: {str(e)}")


@shared_task(name="send_shift_reminders")
def send_shift_reminders():
    """
    Sends reminders for upcoming shifts.
    This task should be called periodically by a scheduler.
    """
    try:
        ShiftManager.send_upcoming_shift_reminders()
        logger.info("Completed sending shift reminders")
    except Exception as e:
        logger.error(f"Error sending shift reminders: {str(e)}")
