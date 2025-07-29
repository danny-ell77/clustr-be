"""
Emergency management utilities for ClustR application.
"""

import logging
from typing import List, Optional
from django.utils import timezone
from django.template import Context
from django.db.models import Q, Count, Avg
from django.utils.translation import gettext_lazy as _

from core.common.models.emergency import (
    EmergencyContact,
    SOSAlert,
    EmergencyResponse,
    EmergencyType,
    EmergencyContactType,
    EmergencyStatus,
)
from core.notifications.manager import NotificationManager
from core.notifications.events import NotificationEvents
from core.common.email_sender import AccountEmailSender, NotificationTypes

logger = logging.getLogger('clustr')


class EmergencyManager:
    """
    Manages emergency contacts and SOS alerts.
    """
    
    @staticmethod
    def get_emergency_contacts_for_type(cluster, emergency_type: str, contact_type: str = None) -> List[EmergencyContact]:
        """
        Get emergency contacts for a specific emergency type.
        
        Args:
            cluster: The cluster object
            emergency_type: Type of emergency
            contact_type: Optional contact type filter
            
        Returns:
            List of emergency contacts
        """
        try:
            queryset = EmergencyContact.objects.filter(
                cluster=cluster,
                is_active=True,
                emergency_types__contains=[emergency_type]
            )
            
            if contact_type:
                queryset = queryset.filter(contact_type=contact_type)
            
            # Order by primary contacts first, then by name
            return queryset.order_by('-is_primary', 'name')
            
        except Exception as e:
            logger.error(f"Failed to get emergency contacts for type {emergency_type}: {e}")
            return []
    
    @staticmethod
    def get_user_emergency_contacts(user) -> List[EmergencyContact]:
        """
        Get emergency contacts for a specific user.
        
        Args:
            user: The user object
            
        Returns:
            List of user's emergency contacts
        """
        try:
            return EmergencyContact.objects.filter(
                cluster=user.cluster,
                user=user,
                is_active=True
            ).order_by('-is_primary', 'name')
            
        except Exception as e:
            logger.error(f"Failed to get emergency contacts for user {user.id}: {e}")
            return []
    
    @staticmethod
    def get_estate_emergency_contacts(cluster, emergency_type: str = None) -> List[EmergencyContact]:
        """
        Get estate-wide emergency contacts.
        
        Args:
            cluster: The cluster object
            emergency_type: Optional emergency type filter
            
        Returns:
            List of estate-wide emergency contacts
        """
        try:
            queryset = EmergencyContact.objects.filter(
                cluster=cluster,
                contact_type=EmergencyContactType.ESTATE_WIDE,
                is_active=True
            )
            
            if emergency_type:
                queryset = queryset.filter(emergency_types__contains=[emergency_type])
            
            return queryset.order_by('-is_primary', 'name')
            
        except Exception as e:
            logger.error(f"Failed to get estate emergency contacts: {e}")
            return []
    
    @staticmethod
    def create_sos_alert(user, emergency_type: str, description: str = "", location: str = "", priority: str = "high") -> Optional[SOSAlert]:
        """
        Create a new SOS alert.
        
        Args:
            user: User triggering the alert
            emergency_type: Type of emergency
            description: Optional description
            location: Optional location
            priority: Priority level
            
        Returns:
            Created SOSAlert object or None if failed
        """
        try:
            alert = SOSAlert.objects.create(
                cluster=user.cluster,
                user=user,
                emergency_type=emergency_type,
                description=description,
                location=location,
                priority=priority,
                created_by=user.id
            )
            
            # Send immediate notifications
            EmergencyManager.send_sos_alert_notifications(alert)
            
            logger.info(f"SOS alert {alert.alert_id} created by user {user.id}")
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create SOS alert: {e}")
            return None
    
    @staticmethod
    def send_sos_alert_notifications(alert: SOSAlert):
        """
        Send notifications for a new SOS alert.
        
        Args:
            alert: The SOS alert object
        """
        try:
            # Get relevant emergency contacts
            contacts = EmergencyManager.get_emergency_contacts_for_type(
                alert.cluster,
                alert.emergency_type
            )
            
            # Get estate-wide contacts
            estate_contacts = EmergencyManager.get_estate_emergency_contacts(
                alert.cluster,
                alert.emergency_type
            )
            
            # Combine contacts and convert to AccountUser objects
            all_contacts = list(contacts) + list(estate_contacts)
            # Has to be direct since Notification manager is only for users with accounts
            AccountEmailSender(
                [contact.email_address for contact in all_contacts], 
                NotificationTypes.EMERGENCY_ALERT
            ).send_to_many(
                {contact.email_address: {
                'alert_id': alert.alert_id,
                'emergency_type': alert.get_emergency_type_display(),
                'user_name': alert.user.name,
                'description': alert.description,
                'location': alert.location,
                'priority': alert.get_priority_display(),
                'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            } for contact in all_contacts}
            )

            recipients = []
            
            # Also notify cluster admins for critical emergencies
            cluster_admins = AccountUser.objects.filter(
                clusters=alert.cluster,
                is_cluster_admin=True
            )
            for admin in cluster_admins:
                if admin not in recipients:
                    recipients.append(admin)
            
            if recipients:
                NotificationManager.send(
                    event=NotificationEvents.EMERGENCY_ALERT,
                    recipients=recipients,
                    cluster=alert.cluster,
                    context={
                        'alert_id': alert.alert_id,
                        'emergency_type': alert.get_emergency_type_display(),
                        'user_name': alert.user.name,
                        'description': alert.description,
                        'location': alert.location,
                        'priority': alert.get_priority_display(),
                        'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                )
            
            logger.info(f"SOS alert notifications sent for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send SOS alert notifications: {e}")
    
    @staticmethod
    def acknowledge_alert(alert: SOSAlert, user) -> bool:
        """
        Acknowledge an SOS alert.
        
        Args:
            alert: The SOS alert to acknowledge
            user: User acknowledging the alert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert.acknowledge(user)
            
            # Send acknowledgment notification
            EmergencyManager.send_alert_status_notification(alert, "acknowledged")
            
            logger.info(f"SOS alert {alert.alert_id} acknowledged by user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge SOS alert {alert.alert_id}: {e}")
            return False
    
    @staticmethod
    def start_response(alert: SOSAlert, user) -> bool:
        """
        Start response to an SOS alert.
        
        Args:
            alert: The SOS alert to respond to
            user: User starting the response
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert.start_response(user)
            
            # Create response record
            EmergencyResponse.objects.create(
                cluster=alert.cluster,
                alert=alert,
                responder=user,
                response_type='dispatched',
                notes=f"Response started by {user.name}",
                created_by=user.id
            )
            
            # Send response notification
            EmergencyManager.send_alert_status_notification(alert, "responding")
            
            logger.info(f"Response started for SOS alert {alert.alert_id} by user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start response for SOS alert {alert.alert_id}: {e}")
            return False
    
    @staticmethod
    def resolve_alert(alert: SOSAlert, user, notes: str = "") -> bool:
        """
        Resolve an SOS alert.
        
        Args:
            alert: The SOS alert to resolve
            user: User resolving the alert
            notes: Resolution notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert.resolve(user, notes)
            
            # Create response record
            EmergencyResponse.objects.create(
                cluster=alert.cluster,
                alert=alert,
                responder=user,
                response_type='resolved',
                notes=notes or f"Alert resolved by {user.name}",
                created_by=user.id
            )
            
            # Send resolution notification
            EmergencyManager.send_alert_status_notification(alert, "resolved")
            
            logger.info(f"SOS alert {alert.alert_id} resolved by user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve SOS alert {alert.alert_id}: {e}")
            return False
    
    @staticmethod
    def cancel_alert(alert: SOSAlert, user, reason: str = "") -> bool:
        """
        Cancel an SOS alert.
        
        Args:
            alert: The SOS alert to cancel
            user: User cancelling the alert
            reason: Cancellation reason
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert.cancel(user, reason)
            
            # Create response record
            EmergencyResponse.objects.create(
                cluster=alert.cluster,
                alert=alert,
                responder=user,
                response_type='cancelled',
                notes=reason or f"Alert cancelled by {user.name}",
                created_by=user.id
            )
            
            # Send cancellation notification
            EmergencyManager.send_alert_status_notification(alert, "cancelled")
            
            logger.info(f"SOS alert {alert.alert_id} cancelled by user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel SOS alert {alert.alert_id}: {e}")
            return False
    
    @staticmethod
    def send_alert_status_notification(alert: SOSAlert, status: str):
        """
        Send notification when alert status changes.
        
        Args:
            alert: The SOS alert
            status: New status
        """
        try:
            recipients = []
            
            # Notify the user who created the alert
            if alert.user:
                recipients.append(alert.user)
            
            # Get relevant emergency contacts and convert to AccountUser objects
            contacts = EmergencyManager.get_emergency_contacts_for_type(
                alert.cluster,
                alert.emergency_type
            )
            
            from accounts.models import AccountUser
            for contact in contacts:
                if contact.email:
                    # Try to find AccountUser by email
                    user = AccountUser.objects.filter(
                        email_address=contact.email,
                        clusters=alert.cluster
                    ).first()
                    if user and user not in recipients:
                        recipients.append(user)
            
            if recipients:
                NotificationManager.send(
                    event=NotificationEvents.EMERGENCY_STATUS_CHANGED,
                    recipients=recipients,
                    cluster=alert.cluster,
                    context={
                        'alert_id': alert.alert_id,
                        'emergency_type': alert.get_emergency_type_display(),
                        'status': status,
                        'user_name': alert.user.name,
                        'status_changed_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to send alert status notification: {e}")
    
    @staticmethod
    def get_active_alerts(cluster) -> List[SOSAlert]:
        """
        Get all active SOS alerts for a cluster.
        
        Args:
            cluster: The cluster object
            
        Returns:
            List of active SOS alerts
        """
        try:
            return SOSAlert.objects.filter(
                cluster=cluster,
                status__in=[EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED, EmergencyStatus.RESPONDING]
            ).order_by('-created_at')
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    @staticmethod
    def get_user_alerts(user, status: str = None) -> List[SOSAlert]:
        """
        Get SOS alerts for a specific user.
        
        Args:
            user: The user object
            status: Optional status filter
            
        Returns:
            List of user's SOS alerts
        """
        try:
            queryset = SOSAlert.objects.filter(
                cluster=user.cluster,
                user=user
            )
            
            if status:
                queryset = queryset.filter(status=status)
            
            return queryset.order_by('-created_at')
            
        except Exception as e:
            logger.error(f"Failed to get user alerts: {e}")
            return []
    
    @staticmethod
    def get_emergency_statistics(cluster) -> dict:
        """
        Get emergency statistics for a cluster.
        
        Args:
            cluster: The cluster object
            
        Returns:
            Dictionary with emergency statistics
        """
        try:
            alerts = SOSAlert.objects.filter(cluster=cluster)
            
            stats = {
                'total_alerts': alerts.count(),
                'active_alerts': alerts.filter(
                    status__in=[EmergencyStatus.ACTIVE, EmergencyStatus.ACKNOWLEDGED, EmergencyStatus.RESPONDING]
                ).count(),
                'resolved_alerts': alerts.filter(status=EmergencyStatus.RESOLVED).count(),
                'cancelled_alerts': alerts.filter(status=EmergencyStatus.CANCELLED).count(),
                'average_response_time': 0,
                'alerts_by_type': {},
                'alerts_by_status': {},
            }
            
            # Calculate average response time
            resolved_alerts = alerts.filter(
                status=EmergencyStatus.RESOLVED,
                responded_at__isnull=False
            )
            
            if resolved_alerts.exists():
                avg_response = resolved_alerts.aggregate(
                    avg_time=Avg('responded_at') - Avg('created_at')
                )
                if avg_response['avg_time']:
                    stats['average_response_time'] = avg_response['avg_time'].total_seconds() / 60
            
            # Get alerts by type
            type_counts = alerts.values('emergency_type').annotate(count=Count('id'))
            for item in type_counts:
                emergency_type = item['emergency_type']
                type_display = dict(EmergencyType.choices).get(emergency_type, emergency_type)
                stats['alerts_by_type'][type_display] = item['count']
            
            # Get alerts by status
            status_counts = alerts.values('status').annotate(count=Count('id'))
            for item in status_counts:
                status = item['status']
                status_display = dict(EmergencyStatus.choices).get(status, status)
                stats['alerts_by_status'][status_display] = item['count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get emergency statistics: {e}")
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'resolved_alerts': 0,
                'cancelled_alerts': 0,
                'average_response_time': 0,
                'alerts_by_type': {},
                'alerts_by_status': {},
            }
    
    @staticmethod
    def check_user_emergency_permissions(user, emergency_type: str) -> bool:
        """
        Check if user has permission to handle a specific emergency type.
        
        Args:
            user: The user object
            emergency_type: Type of emergency
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            from core.common.permissions import CommunicationsPermissions
            
            # Check if user has general emergency management permission
            if user.has_perm(f"core.{CommunicationsPermissions.ManageEmergency}"):
                return True
            
            # Check if user has view permission for emergencies
            if user.has_perm(f"core.{CommunicationsPermissions.ViewEmergency}"):
                return True
            
            # Check if user is security staff
            if user.is_cluster_staff and "security" in user.roles.lower():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check emergency permissions: {e}")
            return False
    
    @staticmethod
    def generate_emergency_report(cluster, start_date=None, end_date=None, emergency_type=None, status=None) -> dict:
        """
        Generate comprehensive emergency report for a cluster.
        
        Args:
            cluster: The cluster object
            start_date: Optional start date filter
            end_date: Optional end date filter
            emergency_type: Optional emergency type filter
            status: Optional status filter
            
        Returns:
            Dictionary with emergency report data
        """
        try:
            from django.db.models import Q, Count, Avg, F
            from django.utils import timezone
            from datetime import timedelta
            
            # Base queryset
            queryset = SOSAlert.objects.filter(cluster=cluster)
            
            # Apply filters
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)
            if emergency_type:
                queryset = queryset.filter(emergency_type=emergency_type)
            if status:
                queryset = queryset.filter(status=status)
            
            # Basic statistics
            total_alerts = queryset.count()
            
            # Status breakdown
            status_breakdown = {}
            for status_choice in EmergencyStatus.choices:
                status_code = status_choice[0]
                status_label = status_choice[1]
                count = queryset.filter(status=status_code).count()
                status_breakdown[status_label] = count
            
            # Emergency type breakdown
            type_breakdown = {}
            for type_choice in EmergencyType.choices:
                type_code = type_choice[0]
                type_label = type_choice[1]
                count = queryset.filter(emergency_type=type_code).count()
                if count > 0:
                    type_breakdown[type_label] = count
            
            # Response time analysis
            resolved_alerts = queryset.filter(
                status=EmergencyStatus.RESOLVED,
                responded_at__isnull=False
            )
            
            response_times = []
            resolution_times = []
            
            for alert in resolved_alerts:
                if alert.response_time_minutes:
                    response_times.append(alert.response_time_minutes)
                if alert.resolution_time_minutes:
                    resolution_times.append(alert.resolution_time_minutes)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            # Time-based analysis
            alerts_by_hour = {}
            alerts_by_day = {}
            alerts_by_month = {}
            
            for alert in queryset:
                # Hour analysis
                hour = alert.created_at.hour
                hour_key = f"{hour:02d}:00"
                alerts_by_hour[hour_key] = alerts_by_hour.get(hour_key, 0) + 1
                
                # Day analysis
                day = alert.created_at.strftime('%A')
                alerts_by_day[day] = alerts_by_day.get(day, 0) + 1
                
                # Month analysis
                month = alert.created_at.strftime('%B %Y')
                alerts_by_month[month] = alerts_by_month.get(month, 0) + 1
            
            # Top responders
            responder_stats = {}
            responses = EmergencyResponse.objects.filter(
                cluster=cluster,
                alert__in=queryset
            ).select_related('responder')
            
            for response in responses:
                responder_name = response.responder.name
                if responder_name not in responder_stats:
                    responder_stats[responder_name] = {
                        'total_responses': 0,
                        'response_types': {}
                    }
                
                responder_stats[responder_name]['total_responses'] += 1
                response_type = response.get_response_type_display()
                responder_stats[responder_name]['response_types'][response_type] = \
                    responder_stats[responder_name]['response_types'].get(response_type, 0) + 1
            
            # Recent alerts summary
            recent_alerts = queryset.order_by('-created_at')[:10]
            recent_alerts_data = []
            
            for alert in recent_alerts:
                recent_alerts_data.append({
                    'alert_id': alert.alert_id,
                    'emergency_type': alert.get_emergency_type_display(),
                    'status': alert.get_status_display(),
                    'user_name': alert.user.name,
                    'created_at': alert.created_at.isoformat(),
                    'response_time_minutes': alert.response_time_minutes,
                    'resolution_time_minutes': alert.resolution_time_minutes,
                })
            
            # Compile report
            report = {
                'report_generated_at': timezone.now().isoformat(),
                'filters': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'emergency_type': emergency_type,
                    'status': status,
                },
                'summary': {
                    'total_alerts': total_alerts,
                    'status_breakdown': status_breakdown,
                    'type_breakdown': type_breakdown,
                    'average_response_time_minutes': round(avg_response_time, 2),
                    'average_resolution_time_minutes': round(avg_resolution_time, 2),
                },
                'time_analysis': {
                    'alerts_by_hour': alerts_by_hour,
                    'alerts_by_day': alerts_by_day,
                    'alerts_by_month': alerts_by_month,
                },
                'responder_analysis': responder_stats,
                'recent_alerts': recent_alerts_data,
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate emergency report: {e}")
            return {
                'error': str(e),
                'report_generated_at': timezone.now().isoformat(),
                'summary': {
                    'total_alerts': 0,
                    'status_breakdown': {},
                    'type_breakdown': {},
                    'average_response_time_minutes': 0,
                    'average_resolution_time_minutes': 0,
                },
            }
    
    @staticmethod
    def generate_alert_incident_report(alert: SOSAlert) -> dict:
        """
        Generate detailed incident report for a specific alert.
        
        Args:
            alert: The SOS alert object
            
        Returns:
            Dictionary with detailed incident report
        """
        try:
            # Get all responses for this alert
            responses = EmergencyResponse.objects.filter(
                alert=alert
            ).order_by('created_at')
            
            # Build timeline
            timeline = []
            
            # Alert creation
            timeline.append({
                'timestamp': alert.created_at.isoformat(),
                'event': 'Alert Created',
                'description': f"SOS alert created by {alert.user.name}",
                'user': alert.user.name,
                'details': {
                    'emergency_type': alert.get_emergency_type_display(),
                    'priority': alert.get_priority_display(),
                    'location': alert.location,
                    'description': alert.description,
                }
            })
            
            # Acknowledgment
            if alert.acknowledged_at:
                timeline.append({
                    'timestamp': alert.acknowledged_at.isoformat(),
                    'event': 'Alert Acknowledged',
                    'description': f"Alert acknowledged by {alert.acknowledged_by.name}",
                    'user': alert.acknowledged_by.name,
                    'details': {}
                })
            
            # Response started
            if alert.responded_at:
                timeline.append({
                    'timestamp': alert.responded_at.isoformat(),
                    'event': 'Response Started',
                    'description': f"Response started by {alert.responded_by.name}",
                    'user': alert.responded_by.name,
                    'details': {}
                })
            
            # All responses
            for response in responses:
                timeline.append({
                    'timestamp': response.created_at.isoformat(),
                    'event': f"Response: {response.get_response_type_display()}",
                    'description': response.notes or f"{response.get_response_type_display()} by {response.responder.name}",
                    'user': response.responder.name,
                    'details': {
                        'response_type': response.get_response_type_display(),
                        'estimated_arrival': response.estimated_arrival.isoformat() if response.estimated_arrival else None,
                        'actual_arrival': response.actual_arrival.isoformat() if response.actual_arrival else None,
                    }
                })
            
            # Resolution or cancellation
            if alert.resolved_at:
                timeline.append({
                    'timestamp': alert.resolved_at.isoformat(),
                    'event': 'Alert Resolved',
                    'description': f"Alert resolved by {alert.resolved_by.name}",
                    'user': alert.resolved_by.name,
                    'details': {
                        'resolution_notes': alert.resolution_notes,
                    }
                })
            elif alert.cancelled_at:
                timeline.append({
                    'timestamp': alert.cancelled_at.isoformat(),
                    'event': 'Alert Cancelled',
                    'description': f"Alert cancelled by {alert.cancelled_by.name}",
                    'user': alert.cancelled_by.name,
                    'details': {
                        'cancellation_reason': alert.cancellation_reason,
                    }
                })
            
            # Sort timeline by timestamp
            timeline.sort(key=lambda x: x['timestamp'])
            
            # Calculate metrics
            metrics = {
                'response_time_minutes': alert.response_time_minutes,
                'resolution_time_minutes': alert.resolution_time_minutes,
                'total_responders': responses.values('responder').distinct().count(),
                'total_responses': responses.count(),
            }
            
            # Get involved contacts
            involved_contacts = EmergencyManager.get_emergency_contacts_for_type(
                alert.cluster,
                alert.emergency_type
            )
            
            contacts_data = []
            for contact in involved_contacts:
                contacts_data.append({
                    'name': contact.name,
                    'phone_number': contact.phone_number,
                    'email': contact.email,
                    'contact_type': contact.get_contact_type_display(),
                    'is_primary': contact.is_primary,
                })
            
            # Compile incident report
            report = {
                'alert_info': {
                    'alert_id': alert.alert_id,
                    'emergency_type': alert.get_emergency_type_display(),
                    'status': alert.get_status_display(),
                    'priority': alert.get_priority_display(),
                    'description': alert.description,
                    'location': alert.location,
                    'created_by': alert.user.name,
                    'created_at': alert.created_at.isoformat(),
                },
                'timeline': timeline,
                'metrics': metrics,
                'involved_contacts': contacts_data,
                'responses_summary': {
                    'total_responses': responses.count(),
                    'response_types': list(responses.values_list('response_type', flat=True)),
                },
                'report_generated_at': timezone.now().isoformat(),
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate incident report for alert {alert.alert_id}: {e}")
            return {
                'error': str(e),
                'alert_id': alert.alert_id,
                'report_generated_at': timezone.now().isoformat(),
            }
    
    @staticmethod
    def _export_report_as_csv(report: dict):
        """
        Export emergency report as CSV format.
        
        Args:
            report: The report dictionary
            
        Returns:
            HTTP response with CSV data
        """
        try:
            import csv
            import io
            from django.http import HttpResponse
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Emergency Report'])
            writer.writerow(['Generated At', report.get('report_generated_at', '')])
            writer.writerow([])
            
            # Write summary
            writer.writerow(['Summary'])
            summary = report.get('summary', {})
            for key, value in summary.items():
                if isinstance(value, dict):
                    writer.writerow([key.replace('_', ' ').title()])
                    for sub_key, sub_value in value.items():
                        writer.writerow(['', sub_key, sub_value])
                else:
                    writer.writerow([key.replace('_', ' ').title(), value])
            
            writer.writerow([])
            
            # Write recent alerts
            writer.writerow(['Recent Alerts'])
            writer.writerow(['Alert ID', 'Emergency Type', 'Status', 'User', 'Created At', 'Response Time (min)', 'Resolution Time (min)'])
            
            for alert in report.get('recent_alerts', []):
                writer.writerow([
                    alert.get('alert_id', ''),
                    alert.get('emergency_type', ''),
                    alert.get('status', ''),
                    alert.get('user_name', ''),
                    alert.get('created_at', ''),
                    alert.get('response_time_minutes', ''),
                    alert.get('resolution_time_minutes', ''),
                ])
            
            # Create response
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="emergency_report.csv"'
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to export report as CSV: {e}")
            from django.http import JsonResponse
            return JsonResponse({'error': 'Failed to export report as CSV'}, status=500)
    
    @staticmethod
    def _export_report_as_pdf(report: dict):
        """
        Export emergency report as PDF format.
        
        Args:
            report: The report dictionary
            
        Returns:
            HTTP response with PDF data
        """
        try:
            from django.http import HttpResponse
            from django.template.loader import render_to_string
            
            # For now, return a simple text-based PDF placeholder
            # In a real implementation, you would use a library like ReportLab or WeasyPrint
            
            content = f"""
Emergency Report
Generated At: {report.get('report_generated_at', '')}

Summary:
Total Alerts: {report.get('summary', {}).get('total_alerts', 0)}
Average Response Time: {report.get('summary', {}).get('average_response_time_minutes', 0)} minutes
Average Resolution Time: {report.get('summary', {}).get('average_resolution_time_minutes', 0)} minutes

Status Breakdown:
"""
            
            for status, count in report.get('summary', {}).get('status_breakdown', {}).items():
                content += f"  {status}: {count}\n"
            
            content += "\nType Breakdown:\n"
            for emergency_type, count in report.get('summary', {}).get('type_breakdown', {}).items():
                content += f"  {emergency_type}: {count}\n"
            
            response = HttpResponse(content, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="emergency_report.pdf"'
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to export report as PDF: {e}")
            from django.http import JsonResponse
            return JsonResponse({'error': 'Failed to export report as PDF'}, status=500)