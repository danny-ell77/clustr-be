"""
Example script demonstrating visitor notification functionality.

This script shows how the new notification system handles visitor-related events
including arrival notifications and overstay alerts.
"""

from datetime import datetime, timedelta
from django.utils import timezone

# Import the new notification system
from core.notifications.events import NotificationEvents
from core.common.includes import notifications

# Import models
from accounts.models import AccountUser
from core.common.models import Visitor, VisitorLog, Cluster


def demonstrate_visitor_arrival_notification():
    """
    Demonstrate how visitor arrival notifications work.
    
    This replaces the old send_visitor_arrival_notification() method.
    """
    print("=== Visitor Arrival Notification Example ===")
    
    # Example data (in real usage, these would come from the database)
    cluster = Cluster.objects.first()  # Get any cluster for demo
    inviting_user = AccountUser.objects.filter(cluster=cluster).first()
    
    if not cluster or not inviting_user:
        print("No test data available. Please ensure you have clusters and users in the database.")
        return
    
    # Create a sample visitor
    visitor = Visitor.objects.create(
        name="John Demo Visitor",
        phone="+1234567890",
        email="demo@example.com",
        estimated_arrival=timezone.now(),
        visit_type=Visitor.VisitType.ONE_TIME,
        invited_by=inviting_user.id,
        cluster=cluster,
        valid_date=(timezone.now() + timedelta(days=1)).date(),
        access_code="DEMO123"
    )
    
    # Create check-in log
    log = VisitorLog.objects.create(
        visitor=visitor,
        log_type=VisitorLog.LogType.CHECKED_IN,
        checked_in_by=inviting_user.id,
        cluster=cluster
    )
    
    # Send arrival notification using new system
    try:
        success = notifications.send(
            event_name=NotificationEvents.VISITOR_ARRIVAL,
            recipients=[inviting_user],
            cluster=cluster,
            context={
                "visitor_name": visitor.name,
                "access_code": visitor.access_code,
                "arrival_time": log.created_at,
                "unit": getattr(inviting_user, 'unit', 'N/A'),
                "checked_in_by": inviting_user.get_full_name() or inviting_user.email_address,
            }
        )
        
        if success:
            print(f"✅ Visitor arrival notification sent successfully for {visitor.name}")
            print(f"   Recipient: {inviting_user.email_address}")
            print(f"   Event: {NotificationEvents.VISITOR_ARRIVAL.value}")
            print(f"   Context: visitor_name={visitor.name}, access_code={visitor.access_code}")
        else:
            print(f"❌ Failed to send visitor arrival notification for {visitor.name}")
            
    except Exception as e:
        print(f"❌ Error sending visitor arrival notification: {str(e)}")
    
    # Clean up demo data
    visitor.delete()


def demonstrate_visitor_overstay_notification():
    """
    Demonstrate how visitor overstay notifications work.
    
    This implements the new send_visitor_overstay_notification() functionality.
    """
    print("\n=== Visitor Overstay Notification Example ===")
    
    # Example data
    cluster = Cluster.objects.first()
    inviting_user = AccountUser.objects.filter(cluster=cluster).first()
    security_user = AccountUser.objects.filter(
        cluster=cluster, 
        role__in=['ADMIN', 'SECURITY', 'MANAGEMENT']
    ).first()
    
    if not cluster or not inviting_user:
        print("No test data available. Please ensure you have clusters and users in the database.")
        return
    
    # Create a sample visitor who has overstayed
    visitor = Visitor.objects.create(
        name="Jane Overstay Visitor",
        phone="+1987654321",
        email="overstay@example.com",
        estimated_arrival=timezone.now() - timedelta(hours=8),
        visit_type=Visitor.VisitType.ONE_TIME,
        invited_by=inviting_user.id,
        cluster=cluster,
        valid_date=(timezone.now() + timedelta(days=1)).date(),
        access_code="OVER123",
        status=Visitor.Status.CHECKED_IN
    )
    
    # Create check-in log from 8 hours ago (overstay for one-time visit)
    checkin_time = timezone.now() - timedelta(hours=8)
    VisitorLog.objects.create(
        visitor=visitor,
        log_type=VisitorLog.LogType.CHECKED_IN,
        checked_in_by=inviting_user.id,
        cluster=cluster,
        created_at=checkin_time
    )
    
    # Calculate overstay duration (8 hours - 4 hours expected = 4 hours overstay)
    overstay_duration = timedelta(hours=4)
    
    # Prepare recipients (inviting user + security/management)
    recipients = [inviting_user]
    if security_user:
        recipients.append(security_user)
    
    # Send overstay notification using new system
    try:
        success = notifications.send(
            event_name=NotificationEvents.VISITOR_OVERSTAY,
            recipients=recipients,
            cluster=cluster,
            context={
                "visitor_name": visitor.name,
                "visitor_phone": visitor.phone,
                "invited_by": inviting_user.get_full_name() or inviting_user.email_address,
                "overstay_duration": str(overstay_duration).split('.')[0],  # Remove microseconds
                "visit_type": visitor.get_visit_type_display(),
                "access_code": visitor.access_code,
                "checkin_time": checkin_time,
            }
        )
        
        if success:
            print(f"✅ Visitor overstay notification sent successfully for {visitor.name}")
            print(f"   Recipients: {[user.email_address for user in recipients]}")
            print(f"   Event: {NotificationEvents.VISITOR_OVERSTAY.value}")
            print(f"   Overstay duration: {overstay_duration}")
            print(f"   Context: visitor_name={visitor.name}, overstay_duration={overstay_duration}")
        else:
            print(f"❌ Failed to send visitor overstay notification for {visitor.name}")
            
    except Exception as e:
        print(f"❌ Error sending visitor overstay notification: {str(e)}")
    
    # Clean up demo data
    visitor.delete()


def show_notification_event_details():
    """Show details about visitor notification events."""
    print("\n=== Visitor Notification Events ===")
    
    from core.notifications.events import NOTIFICATION_EVENTS
    
    visitor_events = [
        NotificationEvents.VISITOR_ARRIVAL,
        NotificationEvents.VISITOR_OVERSTAY
    ]
    
    for event_key in visitor_events:
        event = NOTIFICATION_EVENTS[event_key]
        print(f"\nEvent: {event.name}")
        print(f"  Priority: {event.priority_level} ({event.priority})")
        print(f"  Bypasses preferences: {event.bypasses_preferences}")
        print(f"  Supported channels: {[channel.value for channel in event.supported_channels]}")


if __name__ == "__main__":
    print("Visitor Notification System Demo")
    print("=" * 40)
    
    # Show event details
    show_notification_event_details()
    
    # Demonstrate notifications
    demonstrate_visitor_arrival_notification()
    demonstrate_visitor_overstay_notification()
    
    print("\n=== Migration Summary ===")
    print("✅ VISITOR_ARRIVAL event: Replaces send_visitor_arrival_notification()")
    print("✅ VISITOR_OVERSTAY event: New functionality for overstay detection")
    print("✅ Context data: Updated to match new system requirements")
    print("✅ Management command: monitor_visitors.py for automated overstay detection")
    print("✅ Tests: Created test_visitor_notifications.py for validation")
    
    print("\nMigration complete! Old visitor notification methods have been replaced.")