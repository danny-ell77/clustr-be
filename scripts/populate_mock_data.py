"""
Mock data population script for ClustR backend.

This script populates the database with realistic mock data for:
- Announcements
- Maintenance logs
- Helpdesk issues
- Emergency alerts
- Wallets
- Bills
- Transactions

Run this script with: python manage.py shell < scripts/populate_mock_data.py
Or: python manage.py runscript populate_mock_data (if using django-extensions)
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
from random import choice, randint, sample
from django.utils import timezone
from django.db import transaction
# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import AccountUser
from core.common.models import (
    Cluster,
    Announcement, AnnouncementCategory,
    MaintenanceLog, MaintenanceType, MaintenancePriority, MaintenanceStatus,
    IssueTicket, IssueType, IssuePriority, IssueStatus,
    SOSAlert, EmergencyType, EmergencyStatus,
    Wallet, WalletStatus,
    Bill, BillType, BillCategory, BillStatus,
    Transaction, TransactionType, TransactionStatus, PaymentProvider,
)


def get_existing_user_and_cluster():
    """Get the existing user and their primary cluster."""
    try:
        user = AccountUser.objects.get(email_address="vilofansky@gmail.com")
        print(f"✓ Found existing user: {user.email_address}")
        
        if not user.primary_cluster:
            print("❌ Error: User does not have a primary cluster set!")
            sys.exit(1)
        
        cluster = user.primary_cluster
        print(f"✓ Using user's primary cluster: {cluster.name}")
        return user, cluster
    except AccountUser.DoesNotExist:
        print("❌ Error: User 'vilofansky@gmail.com' not found in database!")
        sys.exit(1)


def create_additional_users(cluster, primary_user, count=10):
    """Create additional test users for the cluster."""
    users = [primary_user]  # Start with the primary user
    
    # Check if primary user is admin, if not, find or create an admin
    if not primary_user.is_cluster_admin:
        admin, created = AccountUser.objects.get_or_create(
            email_address=f"admin@{cluster.name.lower().replace(' ', '')}.com",
            defaults={
                "name": f"{cluster.name} Administrator",
                "phone_number": "+2348012345678",
                "unit_address": "Admin Block A1",
                "is_cluster_admin": True,
                "is_owner": True,
                "is_verified": True,
                "is_phone_verified": True,
                "approved_by_admin": True,
                "primary_cluster": cluster,
            }
        )
        if created:
            admin.set_password("password123")
            admin.save()
            admin.clusters.add(cluster)
            print(f"✓ Created admin user: {admin.email_address}")
        users.append(admin)
    
    # Create regular users
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    last_names = ["Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas"]
    
    for i in range(count - 1):
        first_name = choice(first_names)
        last_name = choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{i}@resident.com"
        
        user, created = AccountUser.objects.get_or_create(
            email_address=email,
            defaults={
                "name": f"{first_name} {last_name}",
                "phone_number": f"+23480{randint(10000000, 99999999)}",
                "unit_address": f"Block {choice(['A', 'B', 'C'])}{randint(1, 50)}",
                "is_owner": True,
                "is_verified": True,
                "is_phone_verified": True,
                "approved_by_admin": True,
                "primary_cluster": cluster,
                "property_owner": choice([True, False]),
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            user.clusters.add(cluster)
        users.append(user)
    
    print(f"✓ Created {len(users)} users")
    return users


def create_announcements(cluster, users, count=15):
    """Create test announcements."""
    announcements = []
    
    titles = [
        ("Security Alert: Increased Patrols", AnnouncementCategory.NEWS, "We have increased security patrols in response to recent incidents."),
        ("Water Supply Interruption", AnnouncementCategory.ESTATE_ISSUES, "Water supply will be interrupted tomorrow from 10 AM to 2 PM for maintenance."),
        ("Community BBQ This Weekend", AnnouncementCategory.NEWS, "Join us for a community BBQ this Saturday at 5 PM in the central park."),
        ("Refuse Collection Schedule Change", AnnouncementCategory.ESTATE_ISSUES, "Refuse collection has been moved to Wednesdays and Saturdays."),
        ("New Gym Equipment Installed", AnnouncementCategory.NEWS, "New state-of-the-art gym equipment has been installed in the fitness center."),
        ("Swimming Pool Maintenance", AnnouncementCategory.ESTATE_ISSUES, "The swimming pool will be closed for cleaning next Monday."),
        ("Estate AGM Invitation", AnnouncementCategory.NEWS, "Annual General Meeting scheduled for next month. All residents invited."),
        ("Power Outage Notice", AnnouncementCategory.ESTATE_ISSUES, "Scheduled power outage on Friday 8 AM - 12 PM for electrical upgrades."),
        ("New Estate Manager Introduction", AnnouncementCategory.NEWS, "Please welcome our new estate manager, Sarah Thompson."),
        ("Parking Violation Reminder", AnnouncementCategory.ESTATE_ISSUES, "Please park only in designated areas to avoid towing."),
        ("Estate Newsletter Available", AnnouncementCategory.OTHERS, "The latest estate newsletter is now available online."),
        ("Children's Playground Upgraded", AnnouncementCategory.NEWS, "The children's playground has been upgraded with new equipment."),
        ("Gate Access System Update", AnnouncementCategory.ESTATE_ISSUES, "The gate access system will be updated to biometric on Monday."),
        ("Fire Safety Drill Scheduled", AnnouncementCategory.NEWS, "Mandatory fire safety drill scheduled for next Wednesday at 10 AM."),
        ("Landscaping Improvements", AnnouncementCategory.NEWS, "New landscaping work begins next week to beautify common areas."),
    ]
    
    for i in range(min(count, len(titles))):
        title, category, content = titles[i]
        days_ago = randint(0, 60)
        published_at = timezone.now() - timedelta(days=days_ago)
        
        announcement = Announcement.objects.create(
            cluster=cluster,
            title=title,
            content=content,
            category=category,
            author_id=choice(users).id,
            views_count=randint(10, 200),
            likes_count=randint(0, 50),
            comments_count=randint(0, 20),
            published_at=published_at,
            is_published=True,
        )
        announcements.append(announcement)
    
    print(f"✓ Created {len(announcements)} announcements")
    return announcements


def create_maintenance_logs(cluster, users, count=20):
    """Create test maintenance logs."""
    logs = []
    
    maintenance_items = [
        ("Generator Servicing", MaintenanceType.PREVENTIVE, "Full servicing of backup generator unit", "Generator Room", "CAT 250KVA"),
        ("Elevator Repair", MaintenanceType.CORRECTIVE, "Repair broken elevator in Block A", "Block A Lobby", "Otis Elevator 2000"),
        ("Pool Filter Replacement", MaintenanceType.ROUTINE, "Replace pool filtration system filters", "Swimming Pool Area", "Hayward Filter"),
        ("Street Light Installation", MaintenanceType.UPGRADE, "Install LED street lights on main road", "Main Road", "Philips LED 100W"),
        ("Fire Alarm Testing", MaintenanceType.INSPECTION, "Quarterly fire alarm system test", "All Buildings", "Honeywell System"),
        ("Pump Emergency Fix", MaintenanceType.EMERGENCY, "Emergency water pump replacement", "Pump House", "Grundfos 50HP"),
        ("CCTV Camera Install", MaintenanceType.UPGRADE, "Install new CCTV cameras at gate 2", "Gate 2 Entrance", "Hikvision 4K"),
        ("Fence Repair", MaintenanceType.CORRECTIVE, "Repair damaged perimeter fence", "North Boundary", "Chain Link Fence"),
        ("Paint Refresh", MaintenanceType.ROUTINE, "Repaint common area walls", "Community Hall", None),
        ("AC Unit Service", MaintenanceType.PREVENTIVE, "Service all AC units in gym", "Fitness Center", "Daikin VRV"),
        ("Door Lock Replacement", MaintenanceType.CORRECTIVE, "Replace malfunctioning main gate lock", "Main Gate", "Smart Lock X200"),
        ("Playground Inspection", MaintenanceType.INSPECTION, "Safety inspection of playground equipment", "Children's Playground", None),
        ("Drainage Cleaning", MaintenanceType.ROUTINE, "Clean drainage system", "Estate Perimeter", None),
        ("Security Booth Upgrade", MaintenanceType.UPGRADE, "Upgrade security booth with AC and new furniture", "Gate 1", None),
        ("Pest Control", MaintenanceType.PREVENTIVE, "Quarterly pest control treatment", "All Common Areas", None),
    ]
    
    staff_users = [u for u in users if u.is_cluster_staff or u.is_cluster_admin]
    if not staff_users:
        staff_users = users[:2]
    
    for i in range(min(count, len(maintenance_items))):
        title, mtype, description, location, equipment = maintenance_items[i]
        days_ago = randint(1, 90)
        scheduled_date = timezone.now() - timedelta(days=days_ago) + timedelta(hours=randint(8, 17))
        
        status = choice([
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.IN_PROGRESS,
            MaintenanceStatus.SCHEDULED,
        ])
        
        log = MaintenanceLog.objects.create(
            cluster=cluster,
            title=title,
            description=description,
            maintenance_type=mtype,
            property_location=location,
            equipment_name=equipment or "",
            priority=choice([p for p in MaintenancePriority]),
            status=status,
            requested_by=choice(users),
            performed_by=choice(staff_users) if status != MaintenanceStatus.SCHEDULED else None,
            supervised_by=choice(staff_users) if status == MaintenanceStatus.COMPLETED else None,
            scheduled_date=scheduled_date,
            started_at=scheduled_date if status != MaintenanceStatus.SCHEDULED else None,
            completed_at=scheduled_date + timedelta(hours=randint(1, 8)) if status == MaintenanceStatus.COMPLETED else None,
            estimated_duration=timedelta(hours=randint(1, 8)),
            cost=Decimal(randint(5000, 500000)) if status == MaintenanceStatus.COMPLETED else None,
            materials_used="Standard materials used" if status == MaintenanceStatus.COMPLETED else "",
            tools_used="Standard tools" if status == MaintenanceStatus.COMPLETED else "",
            notes=f"Work performed by maintenance team",
            completion_notes="Work completed successfully" if status == MaintenanceStatus.COMPLETED else "",
        )
        logs.append(log)
    
    print(f"✓ Created {len(logs)} maintenance logs")
    return logs


def create_helpdesk_issues(cluster, users, count=25):
    """Create test helpdesk issues."""
    issues = []
    
    issue_data = [
        (IssueType.PLUMBING, "Leaking Tap in Block A", "Kitchen tap leaking continuously, needs urgent repair"),
        (IssueType.ELECTRICAL, "Broken Street Light", "Street light near gate 2 not working for 3 days"),
        (IssueType.CLEANING, "Elevator Needs Cleaning", "Elevator in Block B very dirty, needs deep cleaning"),
        (IssueType.CARPENTRY, "Broken Bench", "Wooden bench in park is broken and dangerous"),
        (IssueType.SECURITY, "Gate Access Issue", "Gate 1 access card reader not responding"),
        (IssueType.PLUMBING, "Blocked Drain", "Drain in front of Block C blocked and overflowing"),
        (IssueType.ELECTRICAL, "Power Socket Not Working", "Power sockets in gym not functioning"),
        (IssueType.OTHER, "Noise Complaint", "Excessive noise from Block A construction"),
        (IssueType.CLEANING, "Garbage Overflow", "Garbage bins near Block D overflowing"),
        (IssueType.SECURITY, "Broken CCTV", "CCTV camera 5 not recording"),
        (IssueType.PLUMBING, "Water Pressure Low", "Very low water pressure in Block B"),
        (IssueType.CARPENTRY, "Door Hinge Broken", "Community hall door hinge needs replacement"),
        (IssueType.ELECTRICAL, "Flickering Lights", "Lights in parking area flickering constantly"),
        (IssueType.CLEANING, "Pool Dirty", "Swimming pool needs cleaning, water cloudy"),
        (IssueType.OTHER, "WiFi Not Working", "Community WiFi not working in Block C"),
    ]
    
    staff_users = [u for u in users if u.is_cluster_staff or u.is_cluster_admin]
    if not staff_users:
        staff_users = users[:2]
    
    for i in range(min(count, len(issue_data))):
        issue_type, title, description = issue_data[i % len(issue_data)]
        days_ago = randint(1, 30)
        created_time = timezone.now() - timedelta(days=days_ago)
        
        status = choice([
            IssueStatus.RESOLVED,
            IssueStatus.RESOLVED,
            IssueStatus.IN_PROGRESS,
            IssueStatus.OPEN,
            IssueStatus.SUBMITTED,
        ])
        
        issue = IssueTicket.objects.create(
            cluster=cluster,
            issue_type=issue_type,
            title=title,
            description=description,
            status=status,
            priority=choice([p for p in IssuePriority]),
            reported_by=choice(users),
            assigned_to=choice(staff_users) if status != IssueStatus.SUBMITTED else None,
            resolved_at=created_time + timedelta(hours=randint(2, 72)) if status == IssueStatus.RESOLVED else None,
            due_date=created_time + timedelta(days=randint(1, 7)),
            resolution_notes="Issue resolved successfully" if status == IssueStatus.RESOLVED else "",
        )
        issue.created_at = created_time
        issue.save()
        issues.append(issue)
    
    print(f"✓ Created {len(issues)} helpdesk issues")
    return issues


def create_emergency_alerts(cluster, users, count=10):
    """Create test emergency alerts."""
    alerts = []
    
    emergency_data = [
        (EmergencyType.HEALTH, "Medical Emergency Block A", "Resident needs immediate medical attention"),
        (EmergencyType.THEFT, "Break-in Attempt", "Suspicious activity near Block B, possible break-in"),
        (EmergencyType.FIRE, "Fire in Trash Area", "Small fire in garbage collection area"),
        (EmergencyType.SECURITY, "Unauthorized Access", "Unknown person in restricted area"),
        (EmergencyType.ACCIDENT, "Car Accident at Gate", "Minor car collision at main entrance"),
        (EmergencyType.HEALTH, "Child Injury", "Child fell at playground, requires attention"),
        (EmergencyType.SECURITY, "Vandalism", "Property damage in parking lot"),
        (EmergencyType.FIRE, "Smoke Detected", "Smoke detector activated in Block C"),
        (EmergencyType.DOMESTIC_VIOLENCE, "Disturbance", "Loud disturbance reported in Block A"),
        (EmergencyType.OTHER, "Power Outage Emergency", "Complete power failure during event"),
    ]
    
    staff_users = [u for u in users if u.is_cluster_staff or u.is_cluster_admin]
    if not staff_users:
        staff_users = users[:2]
    
    for i in range(min(count, len(emergency_data))):
        etype, description, details = emergency_data[i]
        days_ago = randint(1, 60)
        created_time = timezone.now() - timedelta(days=days_ago)
        
        status = choice([
            EmergencyStatus.RESOLVED,
            EmergencyStatus.RESOLVED,
            EmergencyStatus.RESOLVED,
            EmergencyStatus.ACTIVE if days_ago < 2 else EmergencyStatus.RESOLVED,
        ])
        
        responder = choice(staff_users)
        alert = SOSAlert.objects.create(
            cluster=cluster,
            user=choice(users),
            emergency_type=etype,
            description=details,
            location=f"Block {choice(['A', 'B', 'C'])}{randint(1, 50)}",
            status=status,
            priority=choice(["high", "critical"]),
            acknowledged_at=created_time + timedelta(minutes=randint(2, 10)) if status != EmergencyStatus.ACTIVE else None,
            acknowledged_by=responder if status != EmergencyStatus.ACTIVE else None,
            responded_at=created_time + timedelta(minutes=randint(5, 20)) if status != EmergencyStatus.ACTIVE else None,
            responded_by=responder if status != EmergencyStatus.ACTIVE else None,
            resolved_at=created_time + timedelta(hours=randint(1, 4)) if status == EmergencyStatus.RESOLVED else None,
            resolved_by=responder if status == EmergencyStatus.RESOLVED else None,
            resolution_notes="Emergency resolved successfully" if status == EmergencyStatus.RESOLVED else "",
        )
        alert.created_at = created_time
        alert.save()
        alerts.append(alert)
    
    print(f"✓ Created {len(alerts)} emergency alerts")
    return alerts


def create_wallets(cluster, users):
    """Create wallets for all users."""
    wallets = []
    
    for user in users:
        wallet, created = Wallet.objects.get_or_create(
            cluster=cluster,
            user_id=user.id,
            defaults={
                "balance": Decimal(randint(0, 500000)),
                "available_balance": Decimal(randint(0, 500000)),
                "currency": "NGN",
                "status": WalletStatus.ACTIVE,
                "is_pin_set": True,
            }
        )
        # Ensure available balance is not greater than balance
        if wallet.available_balance > wallet.balance:
            wallet.available_balance = wallet.balance
            wallet.save()
        wallets.append(wallet)
    
    print(f"✓ Created/verified {len(wallets)} wallets")
    return wallets


def create_bills(cluster, users, wallets, count=30):
    """Create test bills."""
    bills = []
    
    # Cluster-wide bills
    cluster_bill_types = [
        (BillType.ELECTRICITY, "Electricity Bill - January 2025", 150000),
        (BillType.WATER, "Water Bill - January 2025", 80000),
        (BillType.SECURITY, "Security Services - Q1 2025", 200000),
        (BillType.MAINTENANCE, "Estate Maintenance - January", 120000),
        (BillType.SERVICE_CHARGE, "Service Charge - Q1 2025", 250000),
        (BillType.WASTE_MANAGEMENT, "Waste Management - January", 50000),
    ]
    
    for bill_type, title, amount in cluster_bill_types:
        days_ago = randint(5, 30)
        due_date = timezone.now() + timedelta(days=randint(5, 15))
        
        bill = Bill.objects.create(
            cluster=cluster,
            user_id=None,  # Cluster-wide
            title=title,
            description=f"Monthly {bill_type} charges for all residents",
            type=bill_type,
            category=BillCategory.CLUSTER_MANAGED,
            amount=Decimal(amount),
            currency="NGN",
            due_date=due_date,
            allow_payment_after_due=True,
        )
        bill.created_at = timezone.now() - timedelta(days=days_ago)
        bill.save()
        
        # Randomly acknowledge by some users
        acknowledgers = sample(users, k=randint(3, len(users)))
        bill.acknowledged_by.set(acknowledgers)
        
        bills.append(bill)
    
    # User-specific utility bills
    utility_bill_types = [
        (BillType.ELECTRICITY_UTILITY, "PHCN Electricity Bill"),
        (BillType.WATER_UTILITY, "Lagos Water Corporation"),
        (BillType.INTERNET_UTILITY, "Internet Subscription"),
        (BillType.CABLE_TV_UTILITY, "DSTV Subscription"),
    ]
    
    for user in sample(users, k=min(10, len(users))):
        for bill_type, title in sample(utility_bill_types, k=randint(1, 3)):
            days_ago = randint(1, 20)
            due_date = timezone.now() + timedelta(days=randint(3, 10))
            amount = Decimal(randint(5000, 50000))
            
            bill = Bill.objects.create(
                cluster=cluster,
                user_id=user.id,
                title=f"{title} - {user.name}",
                description=f"Utility bill for {user.unit_address}",
                type=bill_type,
                category=BillCategory.USER_MANAGED,
                amount=amount,
                currency="NGN",
                due_date=due_date,
                allow_payment_after_due=True,
                created_by_user=True,
            )
            bill.created_at = timezone.now() - timedelta(days=days_ago)
            bill.save()
            
            # Acknowledge user bills by the user
            bill.acknowledged_by.add(user)
            
            # Randomly mark some as paid
            if randint(0, 100) > 40:
                bill.paid_amount = amount
                bill.paid_at = timezone.now() - timedelta(days=randint(0, 5))
                bill.save()
            
            bills.append(bill)
    
    print(f"✓ Created {len(bills)} bills")
    return bills


def create_transactions(cluster, wallets, count=50):
    """Create test transactions."""
    transactions = []
    
    transaction_types = [
        (TransactionType.DEPOSIT, "Wallet top-up via Paystack"),
        (TransactionType.WITHDRAWAL, "Cash withdrawal"),
        (TransactionType.BILL_PAYMENT, "Electricity bill payment"),
        (TransactionType.BILL_PAYMENT, "Water bill payment"),
        (TransactionType.PAYMENT, "Service payment"),
        (TransactionType.TRANSFER, "Transfer to another user"),
    ]
    
    for i in range(count):
        wallet = choice(wallets)
        ttype, description = choice(transaction_types)
        days_ago = randint(1, 90)
        created_time = timezone.now() - timedelta(days=days_ago)
        
        amount = Decimal(randint(1000, 100000))
        status = choice([
            TransactionStatus.COMPLETED,
            TransactionStatus.COMPLETED,
            TransactionStatus.COMPLETED,
            TransactionStatus.PENDING,
            TransactionStatus.FAILED,
        ])
        
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=ttype,
            amount=amount,
            currency="NGN",
            status=status,
            description=description,
            provider=choice([p for p in PaymentProvider]) if ttype == TransactionType.DEPOSIT else None,
            processed_at=created_time + timedelta(minutes=randint(1, 30)) if status == TransactionStatus.COMPLETED else None,
            failed_at=created_time + timedelta(minutes=randint(1, 10)) if status == TransactionStatus.FAILED else None,
            failure_reason="Insufficient funds" if status == TransactionStatus.FAILED else None,
        )
        transaction.created_at = created_time
        transaction.save()
        transactions.append(transaction)
    
    print(f"✓ Created {len(transactions)} transactions")
    return transactions


def main():
    """Main function to populate all mock data."""
    print("\n" + "="*60)
    print("CLUSTR MOCK DATA POPULATION SCRIPT")
    print("="*60 + "\n")
    
    print("Starting mock data creation...\n")
    
    # Get existing user and cluster
    print("Fetching existing user and cluster...")
    primary_user, cluster = get_existing_user_and_cluster()
    print()
    
    # Create additional users
    print("Creating additional users...")
    users = create_additional_users(cluster, primary_user, count=10)
    print()
    
    # Create announcements
    print("Creating announcements...")
    announcements = create_announcements(cluster, users, count=15)
    print()
    
    # Create maintenance logs
    print("Creating maintenance logs...")
    maintenance_logs = create_maintenance_logs(cluster, users, count=20)
    print()
    
    # Create helpdesk issues
    print("Creating helpdesk issues...")
    issues = create_helpdesk_issues(cluster, users, count=25)
    print()
    
    # Create emergency alerts
    print("Creating emergency alerts...")
    alerts = create_emergency_alerts(cluster, users, count=10)
    print()
    
    # Create wallets
    print("Creating wallets...")
    wallets = create_wallets(cluster, users)
    print()
    
    # Create bills
    print("Creating bills...")
    bills = create_bills(cluster, users, wallets, count=30)
    print()
    
    # Create transactions
    print("Creating transactions...")
    transactions = create_transactions(cluster, wallets, count=50)
    print()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Primary User: {primary_user.email_address} ({primary_user.name})")
    print(f"Cluster: {cluster.name}")
    print(f"Total Users: {len(users)}")
    print(f"Announcements: {len(announcements)}")
    print(f"Maintenance Logs: {len(maintenance_logs)}")
    print(f"Helpdesk Issues: {len(issues)}")
    print(f"Emergency Alerts: {len(alerts)}")
    print(f"Wallets: {len(wallets)}")
    print(f"Bills: {len(bills)}")
    print(f"Transactions: {len(transactions)}")
    print("="*60)
    print("\n✅ Mock data population completed successfully!\n")
    print(f"All data is linked to user: {primary_user.email_address}")
    print(f"In cluster: {cluster.name}\n")


if __name__ == "__main__":
    with transaction.atomic():
        main()
