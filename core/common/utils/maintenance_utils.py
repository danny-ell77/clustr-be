"""
Maintenance utilities for ClustR application.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg

from core.common.models import (
    MaintenanceLog,
    MaintenanceSchedule,
    MaintenanceCost,
    MaintenanceStatus,
    MaintenanceType,
)
from core.common.utils.file_storage import FileStorage
from core.common.models import PropertyType

logger = logging.getLogger("clustr")


class MaintenanceManager:
    """
    Manager for maintenance operations in the ClustR application.
    """

    @staticmethod
    def create_maintenance_log(
        cluster,
        title,
        description,
        maintenance_type,
        property_type,
        property_location,
        requested_by,
        **kwargs,
    ):
        """
        Create a new maintenance log entry.

        Args:
            cluster: The cluster object
            title: Title of the maintenance
            description: Description of the maintenance
            maintenance_type: Type of maintenance
            property_type: Type of property
            property_location: Location of the property
            requested_by: User who requested the maintenance
            **kwargs: Additional fields

        Returns:
            MaintenanceLog object
        """
        try:
            maintenance_log = MaintenanceLog.objects.create(
                cluster=cluster,
                title=title,
                description=description,
                maintenance_type=maintenance_type,
                property_type=property_type,
                property_location=property_location,
                requested_by=requested_by,
                created_by=requested_by.id,
                **kwargs,
            )

            logger.info(
                f"Created maintenance log: {maintenance_log.maintenance_number}"
            )

            # Send notification to assigned staff if any
            if maintenance_log.performed_by:
                MaintenanceManager.send_assignment_notification(maintenance_log)

            return maintenance_log
        except Exception as e:
            logger.error(f"Failed to create maintenance log: {str(e)}")
            raise

    @staticmethod
    def assign_maintenance(maintenance_log, assigned_to, assigned_by=None):
        """
        Assign maintenance to a staff member.

        Args:
            maintenance_log: MaintenanceLog object
            assigned_to: User to assign the maintenance to
            assigned_by: User who made the assignment

        Returns:
            Updated MaintenanceLog object
        """
        try:
            maintenance_log.performed_by = assigned_to
            if assigned_by:
                maintenance_log.last_modified_by = assigned_by.id
            maintenance_log.save()

            # Send assignment notification
            MaintenanceManager.send_assignment_notification(maintenance_log)

            logger.info(
                f"Assigned maintenance {maintenance_log.maintenance_number} to {assigned_to.name}"
            )
            return maintenance_log
        except Exception as e:
            logger.error(f"Failed to assign maintenance: {str(e)}")
            raise

    @staticmethod
    def upload_maintenance_attachment(
        maintenance_log, file_obj, attachment_type, uploaded_by, description=""
    ):
        """
        Upload an attachment for a maintenance log.

        Args:
            maintenance_log: MaintenanceLog object
            file_obj: File object to upload
            attachment_type: Type of attachment
            uploaded_by: User uploading the file
            description: Optional description

        Returns:
            MaintenanceAttachment object
        """
        try:
            # Upload file using FileStorage utility
            file_url = FileStorage.upload_file(
                file_obj,
                folder="maintenance",
                cluster_id=str(maintenance_log.cluster.id),
            )

            # Create attachment record
            from core.common.models import MaintenanceAttachment

            attachment = MaintenanceAttachment.objects.create(
                maintenance_log=maintenance_log,
                file_name=file_obj.name,
                file_url=file_url,
                file_size=file_obj.size,
                file_type=file_obj.content_type,
                uploaded_by=uploaded_by,
                attachment_type=attachment_type,
                description=description,
                cluster=maintenance_log.cluster,
                created_by=uploaded_by.id,
            )

            logger.info(
                f"Uploaded attachment for maintenance {maintenance_log.maintenance_number}"
            )
            return attachment
        except Exception as e:
            logger.error(f"Failed to upload maintenance attachment: {str(e)}")
            raise

    @staticmethod
    def get_maintenance_history(
        cluster,
        property_location=None,
        equipment_name=None,
        property_type=None,
        limit=None,
    ):
        """
        Get maintenance history for a property or equipment.

        Args:
            cluster: The cluster object
            property_location: Optional property location filter
            equipment_name: Optional equipment name filter
            property_type: Optional property type filter
            limit: Optional limit on number of records

        Returns:
            QuerySet of MaintenanceLog objects
        """
        try:
            queryset = MaintenanceLog.objects.filter(cluster=cluster)

            if property_location:
                queryset = queryset.filter(
                    property_location__icontains=property_location
                )

            if equipment_name:
                queryset = queryset.filter(equipment_name__icontains=equipment_name)

            if property_type:
                queryset = queryset.filter(property_type=property_type)

            queryset = queryset.order_by("-created_at")

            if limit:
                queryset = queryset[:limit]

            return queryset
        except Exception as e:
            logger.error(f"Failed to get maintenance history: {str(e)}")
            return MaintenanceLog.objects.none()

    @staticmethod
    def get_maintenance_by_category(cluster, property_type=None, maintenance_type=None):
        """
        Get maintenance logs categorized by property and equipment.

        Args:
            cluster: The cluster object
            property_type: Optional property type filter
            maintenance_type: Optional maintenance type filter

        Returns:
            Dictionary with categorized maintenance data
        """
        try:
            queryset = MaintenanceLog.objects.filter(cluster=cluster)

            if property_type:
                queryset = queryset.filter(property_type=property_type)

            if maintenance_type:
                queryset = queryset.filter(maintenance_type=maintenance_type)

            # Group by property type
            by_property_type = {}
            for log in queryset:
                if log.property_type not in by_property_type:
                    by_property_type[log.property_type] = []
                by_property_type[log.property_type].append(log)

            # Group by equipment
            by_equipment = {}
            for log in queryset.filter(equipment_name__isnull=False).exclude(
                equipment_name=""
            ):
                if log.equipment_name not in by_equipment:
                    by_equipment[log.equipment_name] = []
                by_equipment[log.equipment_name].append(log)

            return {
                "by_property_type": by_property_type,
                "by_equipment": by_equipment,
                "total_count": queryset.count(),
            }
        except Exception as e:
            logger.error(f"Failed to get maintenance by category: {str(e)}")
            return {"by_property_type": {}, "by_equipment": {}, "total_count": 0}

    @staticmethod
    def create_preventive_maintenance_schedule(
        cluster,
        name,
        description,
        property_type,
        property_location,
        frequency_type,
        next_due_date,
        created_by,
        **kwargs,
    ):
        """
        Create a preventive maintenance schedule.

        Args:
            cluster: The cluster object
            name: Name of the schedule
            description: Description of the maintenance
            property_type: Type of property
            property_location: Location of the property
            frequency_type: How often maintenance should occur
            next_due_date: When the next maintenance is due
            created_by: User creating the schedule
            **kwargs: Additional fields

        Returns:
            MaintenanceSchedule object
        """
        try:
            schedule = MaintenanceSchedule.objects.create(
                cluster=cluster,
                name=name,
                description=description,
                property_type=property_type,
                property_location=property_location,
                frequency_type=frequency_type,
                next_due_date=next_due_date,
                created_by=created_by.id,
                **kwargs,
            )

            logger.info(f"Created preventive maintenance schedule: {schedule.name}")
            return schedule
        except Exception as e:
            logger.error(f"Failed to create maintenance schedule: {str(e)}")
            raise

    @staticmethod
    def process_due_maintenance_schedules(cluster):
        """
        Process maintenance schedules that are due and create maintenance logs.

        Args:
            cluster: The cluster object

        Returns:
            List of created MaintenanceLog objects
        """
        try:
            now = timezone.now()
            due_schedules = MaintenanceSchedule.objects.filter(
                cluster=cluster, is_active=True, next_due_date__lte=now
            )

            created_logs = []
            for schedule in due_schedules:
                # Create maintenance log from schedule
                maintenance_log = schedule.create_maintenance_log()
                created_logs.append(maintenance_log)

                # Send notification if assigned
                if maintenance_log.performed_by:
                    MaintenanceManager.send_assignment_notification(maintenance_log)

                logger.info(
                    f"Created scheduled maintenance log: {maintenance_log.maintenance_number}"
                )

            return created_logs
        except Exception as e:
            logger.error(f"Failed to process due maintenance schedules: {str(e)}")
            return []

    @staticmethod
    def send_maintenance_due_alerts(cluster):
        """
        Send alerts for maintenance that is due soon.

        Args:
            cluster: The cluster object

        Returns:
            Number of alerts sent
        """
        try:
            # Get maintenance due within next 24 hours
            now = timezone.now()
            due_soon = now + timedelta(hours=24)

            due_maintenance = MaintenanceLog.objects.filter(
                cluster=cluster,
                status__in=[MaintenanceStatus.SCHEDULED],
                scheduled_date__gte=now,
                scheduled_date__lte=due_soon,
            )

            alerts_sent = 0
            for maintenance in due_maintenance:
                if maintenance.performed_by:
                    success = MaintenanceManager.send_due_reminder(maintenance)
                    if success:
                        alerts_sent += 1

            # Also check preventive maintenance schedules
            due_schedules = MaintenanceSchedule.objects.filter(
                cluster=cluster,
                is_active=True,
                next_due_date__gte=now,
                next_due_date__lte=due_soon,
            )

            for schedule in due_schedules:
                if schedule.assigned_to:
                    success = MaintenanceManager.send_preventive_maintenance_reminder(
                        schedule
                    )
                    if success:
                        alerts_sent += 1

            logger.info(
                f"Sent {alerts_sent} maintenance due alerts for cluster {cluster.name}"
            )
            return alerts_sent
        except Exception as e:
            logger.error(f"Failed to send maintenance due alerts: {str(e)}")
            return 0

    @staticmethod
    def track_maintenance_costs(maintenance_log, cost_items):
        """
        Track detailed costs for a maintenance activity.

        Args:
            maintenance_log: MaintenanceLog object
            cost_items: List of cost item dictionaries

        Returns:
            List of MaintenanceCost objects
        """
        try:
            cost_objects = []
            total_cost = 0

            for item in cost_items:
                cost_obj = MaintenanceCost.objects.create(
                    maintenance_log=maintenance_log,
                    category=item.get("category", "OTHER"),
                    description=item["description"],
                    quantity=item.get("quantity", 1),
                    unit_cost=item["unit_cost"],
                    vendor=item.get("vendor", ""),
                    receipt_number=item.get("receipt_number", ""),
                    date_incurred=item.get("date_incurred", timezone.now().date()),
                    cluster=maintenance_log.cluster,
                    created_by=maintenance_log.last_modified_by,
                )
                cost_objects.append(cost_obj)
                total_cost += cost_obj.total_cost

            # Update maintenance log total cost
            maintenance_log.cost = total_cost
            maintenance_log.save()

            logger.info(
                f"Tracked costs for maintenance {maintenance_log.maintenance_number}: ${total_cost}"
            )
            return cost_objects
        except Exception as e:
            logger.error(f"Failed to track maintenance costs: {str(e)}")
            raise

    @staticmethod
    def get_maintenance_analytics(cluster, start_date=None, end_date=None):
        """
        Get maintenance analytics and patterns.

        Args:
            cluster: The cluster object
            start_date: Optional start date for analysis
            end_date: Optional end date for analysis

        Returns:
            Dictionary with analytics data
        """
        try:
            queryset = MaintenanceLog.objects.filter(cluster=cluster)

            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)

            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)

            # Basic statistics
            total_maintenance = queryset.count()
            completed_maintenance = queryset.filter(
                status=MaintenanceStatus.COMPLETED
            ).count()
            total_cost = queryset.aggregate(total=Sum("cost"))["total"] or 0
            avg_cost = queryset.aggregate(avg=Avg("cost"))["avg"] or 0

            # By type
            by_type = {}
            for choice in MaintenanceType.choices:
                count = queryset.filter(maintenance_type=choice[0]).count()
                by_type[choice[1]] = count

            # By property type
            by_property = {}
            for choice in PropertyType.choices:
                count = queryset.filter(property_type=choice[0]).count()
                by_property[choice[1]] = count

            # By status
            by_status = {}
            for choice in MaintenanceStatus.choices:
                count = queryset.filter(status=choice[0]).count()
                by_status[choice[1]] = count

            # Most frequent maintenance locations
            frequent_locations = (
                queryset.values("property_location")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]
            )

            # Average completion time for completed maintenance
            completed_with_duration = queryset.filter(
                status=MaintenanceStatus.COMPLETED, actual_duration__isnull=False
            )
            avg_duration = completed_with_duration.aggregate(
                avg=Avg("actual_duration")
            )["avg"]

            return {
                "total_maintenance": total_maintenance,
                "completed_maintenance": completed_maintenance,
                "completion_rate": (
                    (completed_maintenance / total_maintenance * 100)
                    if total_maintenance > 0
                    else 0
                ),
                "total_cost": float(total_cost),
                "average_cost": float(avg_cost),
                "by_type": by_type,
                "by_property": by_property,
                "by_status": by_status,
                "frequent_locations": list(frequent_locations),
                "average_duration": avg_duration,
            }
        except Exception as e:
            logger.error(f"Failed to get maintenance analytics: {str(e)}")
            return {}

    @staticmethod
    def suggest_maintenance_optimizations(cluster):
        """
        Analyze maintenance patterns and suggest optimizations.

        Args:
            cluster: The cluster object

        Returns:
            List of optimization suggestions
        """
        try:
            suggestions = []

            # Get maintenance data for analysis
            maintenance_logs = MaintenanceLog.objects.filter(cluster=cluster)

            # Find frequently maintained items
            frequent_items = (
                maintenance_logs.values("property_location", "equipment_name")
                .annotate(count=Count("id"))
                .filter(count__gte=3)
                .order_by("-count")
            )

            for item in frequent_items:
                if item["count"] >= 5:
                    suggestions.append(
                        {
                            "type": "HIGH_FREQUENCY",
                            "message": f"Consider replacing or upgrading {item['equipment_name']} at {item['property_location']} - maintained {item['count']} times",
                            "priority": "HIGH",
                        }
                    )
                elif item["count"] >= 3:
                    suggestions.append(
                        {
                            "type": "PREVENTIVE_SCHEDULE",
                            "message": f"Consider creating a preventive maintenance schedule for {item['equipment_name']} at {item['property_location']}",
                            "priority": "MEDIUM",
                        }
                    )

            # Find high-cost maintenance items
            high_cost_items = (
                maintenance_logs.filter(cost__isnull=False)
                .values("property_location", "equipment_name")
                .annotate(total_cost=Sum("cost"))
                .filter(total_cost__gte=1000)
                .order_by("-total_cost")
            )

            for item in high_cost_items:
                suggestions.append(
                    {
                        "type": "HIGH_COST",
                        "message": f"High maintenance costs for {item['equipment_name']} at {item['property_location']} - total: ${item['total_cost']}",
                        "priority": "HIGH",
                    }
                )

            # Find items without preventive maintenance schedules
            maintained_items = maintenance_logs.values(
                "property_location", "equipment_name"
            ).distinct()
            scheduled_items = MaintenanceSchedule.objects.filter(
                cluster=cluster, is_active=True
            ).values("property_location", "equipment_name")

            for item in maintained_items:
                if item not in scheduled_items and item["equipment_name"]:
                    suggestions.append(
                        {
                            "type": "MISSING_SCHEDULE",
                            "message": f"No preventive maintenance schedule for {item['equipment_name']} at {item['property_location']}",
                            "priority": "LOW",
                        }
                    )

            logger.info(
                f"Generated {len(suggestions)} maintenance optimization suggestions"
            )
            return suggestions
        except Exception as e:
            logger.error(f"Failed to suggest maintenance optimizations: {str(e)}")
            return []

    @staticmethod
    def send_assignment_notification(maintenance_log):
        """
        Send notification when maintenance is assigned.

        Args:
            maintenance_log: MaintenanceLog object

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not maintenance_log.performed_by:
                return False
            
            from core.notifications.manager import NotificationManager
            from core.notifications.events import NotificationEvents
            
            return NotificationManager.send(
                event=NotificationEvents.MAINTENANCE_SCHEDULED,
                recipients=[maintenance_log.performed_by],
                cluster=maintenance_log.cluster,
                context={
                    'maintenance_number': maintenance_log.maintenance_number,
                    'title': maintenance_log.title,
                    'description': maintenance_log.description[:200] + '...' if len(maintenance_log.description) > 200 else maintenance_log.description,
                    'maintenance_type': maintenance_log.get_maintenance_type_display(),
                    'property_type': maintenance_log.get_property_type_display(),
                    'property_location': maintenance_log.property_location,
                    'equipment_name': maintenance_log.equipment_name or 'Not specified',
                    'scheduled_date': maintenance_log.scheduled_date.strftime('%Y-%m-%d %H:%M') if maintenance_log.scheduled_date else 'Not scheduled',
                    'assigned_to_name': maintenance_log.performed_by.name,
                    'requested_by_name': maintenance_log.requested_by.name if maintenance_log.requested_by else 'System',
                }
            )
        except Exception as e:
            logger.error(f"Failed to send assignment notification: {str(e)}")
            return False

    @staticmethod
    def send_due_reminder(maintenance_log):
        """
        Send reminder for maintenance that is due soon.

        Args:
            maintenance_log: MaintenanceLog object

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not maintenance_log.performed_by:
                return False
            
            from core.notifications.manager import NotificationManager
            from core.notifications.events import NotificationEvents
            
            return NotificationManager.send(
                event=NotificationEvents.MAINTENANCE_URGENT,
                recipients=[maintenance_log.performed_by],
                cluster=maintenance_log.cluster,
                context={
                    'maintenance_number': maintenance_log.maintenance_number,
                    'title': maintenance_log.title,
                    'property_location': maintenance_log.property_location,
                    'equipment_name': maintenance_log.equipment_name or 'Not specified',
                    'scheduled_date': maintenance_log.scheduled_date.strftime('%Y-%m-%d %H:%M') if maintenance_log.scheduled_date else 'Not scheduled',
                    'time_remaining': str(maintenance_log.scheduled_date - timezone.now()) if maintenance_log.scheduled_date else 'Overdue',
                    'maintenance_type': maintenance_log.get_maintenance_type_display(),
                    'assigned_to_name': maintenance_log.performed_by.name,
                }
            )
        except Exception as e:
            logger.error(f"Failed to send due reminder: {str(e)}")
            return False

    @staticmethod
    def send_preventive_maintenance_reminder(schedule):
        """
        Send reminder for preventive maintenance that is due.

        Args:
            schedule: MaintenanceSchedule object

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            if not schedule.assigned_to:
                return False
            
            from core.notifications.manager import NotificationManager
            from core.notifications.events import NotificationEvents
            
            return NotificationManager.send(
                event=NotificationEvents.MAINTENANCE_SCHEDULED,
                recipients=[schedule.assigned_to],
                cluster=schedule.cluster,
                context={
                    'schedule_name': schedule.name,
                    'description': schedule.description,
                    'property_location': schedule.property_location,
                    'equipment_name': schedule.equipment_name or 'Not specified',
                    'next_due_date': schedule.next_due_date.strftime('%Y-%m-%d %H:%M') if schedule.next_due_date else 'Not scheduled',
                    'frequency_type': schedule.get_frequency_type_display(),
                    'property_type': schedule.get_property_type_display(),
                    'assigned_to_name': schedule.assigned_to.name,
                }
            )
        except Exception as e:
            logger.error(f"Failed to send preventive maintenance reminder: {str(e)}")
            return False

    @staticmethod
    def send_completion_notification(maintenance_log, completed_by):
        """
        Send notification when maintenance is completed.

        Args:
            maintenance_log: MaintenanceLog object
            completed_by: User who completed the maintenance

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            recipients = []
            
            # Notify the person who requested the maintenance
            if maintenance_log.requested_by and maintenance_log.requested_by != completed_by:
                recipients.append(maintenance_log.requested_by)
            
            if not recipients:
                return True
            
            from core.notifications.manager import NotificationManager
            from core.notifications.events import NotificationEvents
            
            return NotificationManager.send(
                event=NotificationEvents.MAINTENANCE_COMPLETED,
                recipients=recipients,
                cluster=maintenance_log.cluster,
                context={
                    'maintenance_number': maintenance_log.maintenance_number,
                    'title': maintenance_log.title,
                    'property_location': maintenance_log.property_location,
                    'equipment_name': maintenance_log.equipment_name or 'Not specified',
                    'completed_date': maintenance_log.completed_at.strftime('%Y-%m-%d %H:%M') if maintenance_log.completed_at else timezone.now().strftime('%Y-%m-%d %H:%M'),
                    'completed_by_name': completed_by.name,
                    'maintenance_type': maintenance_log.get_maintenance_type_display(),
                    'completion_notes': maintenance_log.completion_notes or 'No additional notes',
                    'cost': f"${maintenance_log.cost:.2f}" if maintenance_log.cost else 'Not specified',
                }
            )
        except Exception as e:
            logger.error(f"Failed to send completion notification: {str(e)}")
            return False
