"""
Django management command to monitor task deadlines and send reminders.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.common.utils.scheduled_tasks import ScheduledTaskManager


class Command(BaseCommand):
    help = 'Monitor task deadlines, send reminders, and process overdue tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cluster-id',
            type=str,
            help='Specific cluster ID to process (optional)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting task monitoring at {timezone.now()}'
            )
        )

        try:
            # Run task deadline checks
            ScheduledTaskManager.check_task_deadlines()
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Task monitoring completed successfully'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error during task monitoring: {str(e)}'
                )
            )
            raise