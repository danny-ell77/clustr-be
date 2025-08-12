"""
Management command to monitor visitor overstays and send notifications.

This command should be run periodically (e.g., every hour) to check for visitors
who have overstayed their expected visit duration and send appropriate notifications.
"""

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AccountUser
from core.common.models import Visitor, VisitorLog, Cluster
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor visitor overstays and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cluster',
            type=str,
            help='Specific cluster ID to monitor (optional)',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Hours after expected departure to consider overstay (default: 4)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without sending notifications',
        )

    def handle(self, *args, **options):
        cluster_id = options.get('cluster')
        overstay_hours = options.get('hours', 4)
        dry_run = options.get('dry_run', False)

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting visitor overstay monitoring (overstay threshold: {overstay_hours} hours)'
            )
        )

        # Get clusters to monitor
        if cluster_id:
            try:
                clusters = [Cluster.objects.get(id=cluster_id)]
            except Cluster.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Cluster with ID {cluster_id} not found')
                )
                return
        else:
            clusters = Cluster.objects.all()

        total_overstays = 0
        total_notifications = 0

        for cluster in clusters:
            overstays, notifications = self._monitor_cluster_visitors(
                cluster, overstay_hours, dry_run
            )
            total_overstays += overstays
            total_notifications += notifications

        self.stdout.write(
            self.style.SUCCESS(
                f'Monitoring complete. Found {total_overstays} overstays, '
                f'sent {total_notifications} notifications'
            )
        )

    def _monitor_cluster_visitors(self, cluster, overstay_hours, dry_run):
        """Monitor visitors for a specific cluster."""
        self.stdout.write(f'Monitoring cluster: {cluster.name}')

        # Find visitors who are currently checked in
        checked_in_visitors = Visitor.objects.filter(
            cluster=cluster,
            status=Visitor.Status.CHECKED_IN
        )

        overstays_found = 0
        notifications_sent = 0
        overstay_threshold = timedelta(hours=overstay_hours)

        for visitor in checked_in_visitors:
            # Get the latest check-in log
            latest_checkin = VisitorLog.objects.filter(
                visitor=visitor,
                log_type=VisitorLog.LogType.CHECKED_IN
            ).order_by('-created_at').first()

            if not latest_checkin:
                continue

            # Calculate expected departure time based on visit type
            expected_departure = self._calculate_expected_departure(
                visitor, latest_checkin.created_at
            )

            # Check if visitor has overstayed
            current_time = timezone.now()
            if current_time > (expected_departure + overstay_threshold):
                overstays_found += 1
                overstay_duration = current_time - expected_departure

                self.stdout.write(
                    f'  Overstay detected: {visitor.name} '
                    f'(overstayed by {overstay_duration})'
                )

                if not dry_run:
                    # Send overstay notification
                    if self._send_overstay_notification(visitor, overstay_duration):
                        notifications_sent += 1

        return overstays_found, notifications_sent

    def _calculate_expected_departure(self, visitor, checkin_time):
        """Calculate expected departure time based on visit type."""
        if visitor.visit_type == Visitor.VisitType.ONE_TIME:
            # One-time visits expected to last 4 hours
            return checkin_time + timedelta(hours=4)
        elif visitor.visit_type == Visitor.VisitType.SHORT_STAY:
            # Short stays expected to last 8 hours
            return checkin_time + timedelta(hours=8)
        elif visitor.visit_type == Visitor.VisitType.EXTENDED_STAY:
            # Extended stays expected to last until end of valid date
            return timezone.make_aware(
                datetime.combine(visitor.valid_date, datetime.min.time())
            ) + timedelta(days=1)
        else:
            # Default to 4 hours
            return checkin_time + timedelta(hours=4)

    def _send_overstay_notification(self, visitor, overstay_duration):
        """Send overstay notification to relevant parties."""
        try:
            # Get the user who invited the visitor
            inviting_user = AccountUser.objects.get(id=visitor.invited_by)

            # Get security/management users for the cluster
            management_users = AccountUser.objects.filter(
                cluster=visitor.cluster,
                role__in=['ADMIN', 'SECURITY', 'MANAGEMENT']
            )

            # Combine recipients
            recipients = [inviting_user] + list(management_users)

            # Send notification
            success = notifications.send(
                event_name=NotificationEvents.VISITOR_OVERSTAY,
                recipients=recipients,
                cluster=visitor.cluster,
                context={
                    "visitor_name": visitor.name,
                    "visitor_phone": visitor.phone,
                    "invited_by": inviting_user.get_full_name() or inviting_user.email_address,
                    "overstay_duration": str(overstay_duration).split('.')[0],  # Remove microseconds
                    "visit_type": visitor.get_visit_type_display(),
                    "access_code": visitor.access_code,
                    "checkin_time": visitor.logs.filter(
                        log_type=VisitorLog.LogType.CHECKED_IN
                    ).order_by('-created_at').first().created_at,
                }
            )

            if success:
                logger.info(f"Overstay notification sent for visitor {visitor.name}")
                return True
            else:
                logger.error(f"Failed to send overstay notification for visitor {visitor.name}")
                return False

        except AccountUser.DoesNotExist:
            logger.error(f"Inviting user not found for visitor {visitor.name}")
            return False
        except Exception as e:
            logger.error(f"Error sending overstay notification for visitor {visitor.name}: {str(e)}")
            return False