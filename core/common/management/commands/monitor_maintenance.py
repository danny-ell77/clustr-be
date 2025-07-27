"""
Django management command to monitor maintenance schedules and send alerts.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.common.models import Cluster
from core.common.utils.maintenance_utils import MaintenanceManager

logger = logging.getLogger('clustr')


class Command(BaseCommand):
    help = 'Monitor maintenance schedules and send alerts for due maintenance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cluster',
            type=str,
            help='Specific cluster ID to process (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without making changes',
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        cluster_id = options.get('cluster')
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting maintenance monitoring at {timezone.now()}"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode - no changes will be made")
            )
        
        try:
            # Get clusters to process
            if cluster_id:
                try:
                    clusters = [Cluster.objects.get(id=cluster_id)]
                    self.stdout.write(f"Processing specific cluster: {clusters[0].name}")
                except Cluster.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Cluster with ID {cluster_id} not found")
                    )
                    return
            else:
                clusters = Cluster.objects.all()
                self.stdout.write(f"Processing {clusters.count()} clusters")
            
            total_logs_created = 0
            total_alerts_sent = 0
            
            for cluster in clusters:
                self.stdout.write(f"\nProcessing cluster: {cluster.name}")
                
                # Process due maintenance schedules
                if not dry_run:
                    created_logs = MaintenanceManager.process_due_maintenance_schedules(cluster)
                    logs_created = len(created_logs)
                    total_logs_created += logs_created
                    
                    if logs_created > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Created {logs_created} maintenance logs from schedules"
                            )
                        )
                        
                        # Log details of created maintenance logs
                        for log in created_logs:
                            self.stdout.write(f"    - {log.maintenance_number}: {log.title}")
                    else:
                        self.stdout.write("  No due maintenance schedules found")
                else:
                    # In dry-run mode, just check what would be processed
                    from core.common.models import MaintenanceSchedule
                    now = timezone.now()
                    due_schedules = MaintenanceSchedule.objects.filter(
                        cluster=cluster,
                        is_active=True,
                        next_due_date__lte=now
                    )
                    
                    if due_schedules.exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Would create {due_schedules.count()} maintenance logs from schedules:"
                            )
                        )
                        for schedule in due_schedules:
                            self.stdout.write(f"    - {schedule.name} at {schedule.property_location}")
                    else:
                        self.stdout.write("  No due maintenance schedules found")
                
                # Send maintenance due alerts
                if not dry_run:
                    alerts_sent = MaintenanceManager.send_maintenance_due_alerts(cluster)
                    total_alerts_sent += alerts_sent
                    
                    if alerts_sent > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Sent {alerts_sent} maintenance due alerts"
                            )
                        )
                    else:
                        self.stdout.write("  No maintenance due alerts to send")
                else:
                    # In dry-run mode, just check what alerts would be sent
                    from core.common.models import MaintenanceLog, MaintenanceStatus
                    from datetime import timedelta
                    
                    now = timezone.now()
                    due_soon = now + timedelta(hours=24)
                    
                    due_maintenance = MaintenanceLog.objects.filter(
                        cluster=cluster,
                        status__in=[MaintenanceStatus.SCHEDULED],
                        scheduled_date__gte=now,
                        scheduled_date__lte=due_soon,
                        performed_by__isnull=False
                    )
                    
                    if due_maintenance.exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Would send {due_maintenance.count()} maintenance due alerts:"
                            )
                        )
                        for maintenance in due_maintenance:
                            self.stdout.write(
                                f"    - {maintenance.maintenance_number}: {maintenance.title} "
                                f"(due: {maintenance.scheduled_date})"
                            )
                    else:
                        self.stdout.write("  No maintenance due alerts to send")
            
            # Summary
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(self.style.SUCCESS("MAINTENANCE MONITORING SUMMARY"))
            self.stdout.write(f"{'='*50}")
            self.stdout.write(f"Clusters processed: {len(clusters)}")
            
            if not dry_run:
                self.stdout.write(f"Maintenance logs created: {total_logs_created}")
                self.stdout.write(f"Alerts sent: {total_alerts_sent}")
            else:
                self.stdout.write("Mode: DRY-RUN (no changes made)")
            
            self.stdout.write(f"Completed at: {timezone.now()}")
            
        except Exception as e:
            logger.error(f"Error in maintenance monitoring command: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Error occurred: {str(e)}")
            )
            raise
    
    def log_maintenance_analytics(self, cluster):
        """Log maintenance analytics for the cluster."""
        try:
            analytics = MaintenanceManager.get_maintenance_analytics(cluster)
            
            self.stdout.write(f"\n  Maintenance Analytics for {cluster.name}:")
            self.stdout.write(f"    Total maintenance: {analytics.get('total_maintenance', 0)}")
            self.stdout.write(f"    Completed: {analytics.get('completed_maintenance', 0)}")
            self.stdout.write(f"    Completion rate: {analytics.get('completion_rate', 0):.1f}%")
            self.stdout.write(f"    Total cost: ${analytics.get('total_cost', 0):.2f}")
            self.stdout.write(f"    Average cost: ${analytics.get('average_cost', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Error getting maintenance analytics: {str(e)}")
            self.stdout.write(
                self.style.WARNING(f"    Could not retrieve analytics: {str(e)}")
            )