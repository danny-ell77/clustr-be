"""
Management command to process recurring utility payments.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from core.common.models import RecurringPayment, RecurringPaymentStatus

logger = logging.getLogger("clustr")


class Command(BaseCommand):
    help = "Process due recurring utility payments"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without making actual payments',
        )
        parser.add_argument(
            '--cluster-id',
            type=str,
            help='Process payments for specific cluster only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cluster_id = options.get('cluster_id')

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting utility payment processing {'(DRY RUN)' if dry_run else ''}"
            )
        )

        # Get due recurring payments
        queryset = RecurringPayment.objects.filter(
            status=RecurringPaymentStatus.ACTIVE,
            next_payment_date__lte=timezone.now(),
            utility_provider__isnull=False  # Only utility payments
        ).select_related('utility_provider', 'wallet')

        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)

        due_payments = queryset.order_by('next_payment_date')
        total_payments = due_payments.count()

        if total_payments == 0:
            self.stdout.write(
                self.style.WARNING("No due utility payments found")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {total_payments} due utility payments")
        )

        successful_payments = 0
        failed_payments = 0

        for payment in due_payments:
            try:
                with transaction.atomic():
                    self.stdout.write(
                        f"Processing payment: {payment.title} - "
                        f"{payment.currency} {payment.amount} for user {payment.user_id}"
                    )

                    if not dry_run:
                        success = payment.process_payment()
                        if success:
                            successful_payments += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"✓ Payment processed successfully")
                            )
                        else:
                            failed_payments += 1
                            self.stdout.write(
                                self.style.ERROR(f"✗ Payment failed")
                            )
                    else:
                        # In dry-run mode, just log what would happen
                        self.stdout.write(
                            self.style.WARNING(f"[DRY RUN] Would process payment")
                        )
                        successful_payments += 1

            except Exception as e:
                failed_payments += 1
                logger.error(f"Error processing payment {payment.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing payment: {str(e)}")
                )

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"Payment processing completed {'(DRY RUN)' if dry_run else ''}"
            )
        )
        self.stdout.write(f"Total payments processed: {total_payments}")
        self.stdout.write(
            self.style.SUCCESS(f"Successful payments: {successful_payments}")
        )
        if failed_payments > 0:
            self.stdout.write(
                self.style.ERROR(f"Failed payments: {failed_payments}")
            )

        # Check for payments that need attention
        paused_payments = RecurringPayment.objects.filter(
            status=RecurringPaymentStatus.PAUSED,
            utility_provider__isnull=False,
            failed_attempts__gte=3
        ).count()

        if paused_payments > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nWarning: {paused_payments} utility payments are paused due to failures"
                )
            )

        self.stdout.write("="*50)