"""
Management command to process payment-related scheduled tasks.
"""

import logging
from django.core.management.base import BaseCommand
from core.common.includes import recurring_payments, bills
from core.common.models import Cluster

logger = logging.getLogger('clustr')


class Command(BaseCommand):
    help = 'Process payment-related scheduled tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=[
                'recurring_payments',
                'recurring_reminders',
                'overdue_bills',
                'bill_reminders',
                'all'
            ],
            default='all',
            help='Specific payment task to run (default: all)'
        )

    def handle(self, *args, **options):
        task = options['task']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting payment task: {task}')
        )
        
        try:
            if task == 'recurring_payments' or task == 'all':
                self.stdout.write('Processing recurring payments...')
                for cluster in Cluster.objects.all():
                    recurring_payments.process_due_payments(cluster)
                self.stdout.write(
                    self.style.SUCCESS('✓ Recurring payments processed')
                )
            
            if task == 'recurring_reminders' or task == 'all':
                self.stdout.write('Sending recurring payment reminders...')
                for cluster in Cluster.objects.all():
                    recurring_payments.send_payment_reminders(cluster, days_before=1)
                self.stdout.write(
                    self.style.SUCCESS('✓ Recurring payment reminders sent')
                )
            
            if task == 'overdue_bills' or task == 'all':
                self.stdout.write('Checking overdue bills...')
                for cluster in Cluster.objects.all():
                    bills.check_and_update_overdue(cluster)
                self.stdout.write(
                    self.style.SUCCESS('✓ Overdue bills checked')
                )
            
            if task == 'bill_reminders' or task == 'all':
                self.stdout.write('Sending bill reminders...')
                for cluster in Cluster.objects.all():
                    bills.send_reminders(cluster, days_before_due=3)
                self.stdout.write(
                    self.style.SUCCESS('✓ Bill reminders sent')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Payment task "{task}" completed successfully')
            )
            
        except Exception as e:
            logger.error(f'Error running payment task "{task}": {e}')
            self.stdout.write(
                self.style.ERROR(f'Error running payment task "{task}": {e}')
            )
            raise