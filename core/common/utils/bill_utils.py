"""
Bill management utilities for ClustR application.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum

from core.common.models import (
    Bill,
    BillStatus,
    BillType,
    Transaction,
    TransactionType,
    Wallet,
)
from core.notifications.events import NotificationEvents
from core.notifications.manager import NotificationManager

logger = logging.getLogger('clustr')


class BillManager:
    """
    Manager for handling bill operations.
    """
    
    @staticmethod
    def create_cluster_wide_bill(cluster, title: str, amount: Decimal,
                               bill_type: BillType, due_date, description: str = None,
                               allow_payment_after_due: bool = True,
                               created_by: str = None, metadata: Optional[dict] = None) -> Bill:
        """
        Create a new cluster-wide bill that applies to all cluster members.
        This creates only ONE record regardless of the number of users in the cluster.
        
        Args:
            cluster: Estate object
            title: Bill title
            amount: Bill amount
            bill_type: Type of bill
            due_date: Bill due date
            description: Bill description
            allow_payment_after_due: Whether payment is allowed after due date
            created_by: ID of the user creating the bill
            metadata: Additional bill metadata
            
        Returns:
            Bill: Created bill object
        """
        bill = Bill.objects.create(
            cluster=cluster,
            user_id=None,  # Estate-wide bills have no specific user
            title=title,
            description=description,
            type=bill_type,
            amount=amount,
            due_date=due_date,
            allow_payment_after_due=allow_payment_after_due,
            metadata=metadata or {},
            created_by=created_by,
            last_modified_by=created_by,
        )
        
        logger.info(f"Estate-wide bill created: {bill.bill_number} for cluster {cluster.name}")
        
        # Send notification to all cluster members
        BillNotificationManager.send_cluster_wide_bill_notification(bill)
        
        return bill
    
    @staticmethod
    def create_user_specific_bill(cluster, user_id: str, title: str, amount: Decimal,
                                 bill_type: BillType, due_date, description: str = None,
                                 allow_payment_after_due: bool = True,
                                 created_by: str = None, metadata: Optional[dict] = None) -> Bill:
        """
        Create a new user-specific bill that applies to only one user.
        
        Args:
            cluster: Estate object
            user_id: ID of the user the bill is for
            title: Bill title
            amount: Bill amount
            bill_type: Type of bill
            due_date: Bill due date
            description: Bill description
            allow_payment_after_due: Whether payment is allowed after due date
            created_by: ID of the user creating the bill
            metadata: Additional bill metadata
            
        Returns:
            Bill: Created bill object
        """
        bill = Bill.objects.create(
            cluster=cluster,
            user_id=user_id,  # User-specific bills target a specific user
            title=title,
            description=description,
            type=bill_type,
            amount=amount,
            due_date=due_date,
            allow_payment_after_due=allow_payment_after_due,
            metadata=metadata or {},
            created_by=created_by,
            last_modified_by=created_by,
        )
        
        logger.info(f"User-specific bill created: {bill.bill_number} for user {user_id}")
        
        # Send notification to the specific user
        BillNotificationManager.send_user_specific_bill_notification(bill)
        
        return bill
    
    @staticmethod
    def create_bill(cluster, user_id: str, title: str, amount: Decimal,
                   bill_type: BillType, due_date, description: str = None,
                   created_by: str = None, metadata: Optional[dict] = None) -> Bill:
        """
        Create a new bill for a user.
        
        Args:
            cluster: Cluster object
            user_id: ID of the user the bill is for
            title: Bill title
            amount: Bill amount
            bill_type: Type of bill
            due_date: Bill due date
            description: Bill description
            created_by: ID of the user creating the bill
            metadata: Additional bill metadata
            
        Returns:
            Bill: Created bill object
        """
        bill = Bill.objects.create(
            cluster=cluster,
            user_id=user_id,
            title=title,
            description=description,
            type=bill_type,
            amount=amount,
            due_date=due_date,
            status=BillStatus.PENDING_ACKNOWLEDGMENT,
            metadata=metadata or {},
            created_by=created_by,
            last_modified_by=created_by,
        )
        
        logger.info(f"Bill created: {bill.bill_number} for user {user_id}")
        
        # Send notification to user
        BillNotificationManager.send_new_bill_notification(bill)
        
        return bill
    
    @staticmethod
    def create_bulk_bills(cluster, user_bills: List[Dict], created_by: str = None) -> List[Bill]:
        """
        Create multiple bills at once.
        
        Args:
            cluster: Cluster object
            user_bills: List of bill data dictionaries
            created_by: ID of the user creating the bills
            
        Returns:
            List[Bill]: Created bill objects
        """
        bills = []
        
        for bill_data in user_bills:
            try:
                bill = BillManager.create_bill(
                    cluster=cluster,
                    user_id=bill_data['user_id'],
                    title=bill_data['title'],
                    amount=bill_data['amount'],
                    bill_type=bill_data['type'],
                    due_date=bill_data['due_date'],
                    description=bill_data.get('description'),
                    created_by=created_by,
                    metadata=bill_data.get('metadata'),
                )
                bills.append(bill)
            except Exception as e:
                logger.error(f"Failed to create bill for user {bill_data.get('user_id')}: {e}")
        
        logger.info(f"Created {len(bills)} bills out of {len(user_bills)} requested")
        
        return bills
    
    @staticmethod
    def update_bill_status(bill: Bill, new_status: BillStatus, updated_by: str = None) -> bool:
        """
        Update bill status.
        
        Args:
            bill: Bill object to update
            new_status: New bill status
            updated_by: ID of the user updating the bill
            
        Returns:
            bool: True if update was successful
        """
        old_status = bill.status
        bill.status = new_status
        bill.last_modified_by = updated_by
        bill.save()
        
        logger.info(f"Bill {bill.bill_number} status changed from {old_status} to {new_status}")
        
        # Send notification for status changes
        if new_status == BillStatus.OVERDUE:
            BillNotificationManager.send_overdue_bill_notification(bill)
        elif new_status == BillStatus.CANCELLED:
            BillNotificationManager.send_bill_cancelled_notification(bill)
        
        return True
    
    @staticmethod
    def get_user_bills(cluster, user_id: str, status: BillStatus = None,
                      bill_type: BillType = None, limit: int = None) -> List[Bill]:
        """
        Get bills for a specific user.
        
        Args:
            cluster: Cluster object
            user_id: User ID
            status: Filter by bill status
            bill_type: Filter by bill type
            limit: Limit number of results
            
        Returns:
            List[Bill]: User's bills
        """
        queryset = Bill.objects.filter(cluster=cluster, user_id=user_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if bill_type:
            queryset = queryset.filter(type=bill_type)
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    @staticmethod
    def get_overdue_bills(cluster, user_id: str = None) -> List[Bill]:
        """
        Get overdue bills.
        
        Args:
            cluster: Cluster object
            user_id: Optional user ID to filter by
            
        Returns:
            List[Bill]: Overdue bills
        """
        queryset = Bill.objects.filter(
            cluster=cluster,
            due_date__lt=timezone.now(),
            status__in=[BillStatus.ACKNOWLEDGED, BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
        )
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return list(queryset)
    
    @staticmethod
    def get_bills_summary(cluster, user_id: str) -> dict[str, Any]:
        """
        Get bills summary for a user.
        
        Args:
            cluster: Cluster object
            user_id: User ID
            
        Returns:
            Dict: Bills summary
        """
        bills = Bill.objects.filter(cluster=cluster, user_id=user_id)
        
        summary = {
            'total_bills': bills.count(),
            'pending_bills': bills.filter(status=BillStatus.PENDING).count(),
            'overdue_bills': bills.filter(
                status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID],
                due_date__lt=timezone.now()
            ).count(),
            'paid_bills': bills.filter(status=BillStatus.PAID).count(),
            'total_amount_due': bills.filter(
                status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID, BillStatus.OVERDUE]
            ).aggregate(
                total=Sum('amount') - Sum('paid_amount')
            )['total'] or Decimal('0.00'),
            'total_paid': bills.filter(status=BillStatus.PAID).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
        }
        
        return summary
    
    @staticmethod
    def process_bill_payment(bill: Bill, wallet: Wallet, amount: Decimal = None, user=None) -> Transaction:
        """
        Process payment for a bill using wallet balance.
        
        Args:
            bill: Bill to pay
            wallet: Wallet to debit
            amount: Amount to pay (defaults to remaining amount)
            user: User making the payment (for validation)
            
        Returns:
            Transaction: Payment transaction
        """
        if amount is None:
            amount = bill.remaining_amount
        
        if amount <= 0:
            raise ValueError("Payment amount must be greater than 0")
        
        if amount > bill.remaining_amount:
            raise ValueError("Payment amount cannot exceed remaining bill amount")
        
        if not wallet.has_sufficient_balance(amount):
            raise ValueError("Insufficient wallet balance")
        
        # New validation: Check if user can pay this bill
        if user and not bill.can_be_paid_by(user):
            if not bill.acknowledged_by.filter(id=user.id).exists():
                raise ValueError("Bill must be acknowledged before payment")
            elif bill.is_overdue and not bill.allow_payment_after_due:
                raise ValueError("Payment not allowed after due date")
            else:
                raise ValueError("You are not authorized to pay this bill")
        
        # Validate transaction can pay this bill
        if not bill.can_be_paid():
            if bill.is_fully_paid:
                raise ValueError("Bill is already fully paid")
            elif bill.is_disputed:
                raise ValueError("Cannot pay disputed bill")
            else:
                raise ValueError("Bill cannot be paid")
        
        # Create transaction
        transaction = Transaction.objects.create(
            cluster=wallet.cluster,
            wallet=wallet,
            type=TransactionType.BILL_PAYMENT,
            amount=amount,
            currency=wallet.currency,
            description=f"Bill payment: {bill.title}",
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            created_by=wallet.created_by,
            last_modified_by=wallet.last_modified_by,
        )
        
        # Update wallet balance
        wallet.update_balance(amount, TransactionType.BILL_PAYMENT)
        
        # Update bill with transaction linking
        bill.add_payment(amount, transaction)
        
        logger.info(f"Bill payment processed: {transaction.transaction_id} for bill {bill.bill_number}")
        
        # Send payment confirmation
        BillNotificationManager.send_payment_confirmation(bill, transaction)
        
        return transaction
        return transaction
    
    @staticmethod
    def check_and_update_overdue_bills(cluster) -> int:
        """
        Check for overdue bills and update their status.
        
        Args:
            cluster: Cluster object
            
        Returns:
            int: Number of bills marked as overdue
        """
        overdue_bills = Bill.objects.filter(
            cluster=cluster,
            due_date__lt=timezone.now(),
            status=BillStatus.PENDING
        )
        
        count = 0
        for bill in overdue_bills:
            BillManager.update_bill_status(bill, BillStatus.OVERDUE)
            count += 1
        
        logger.info(f"Marked {count} bills as overdue in cluster {cluster.id}")
        
        return count
    
    @staticmethod
    def send_bill_reminders(cluster, days_before_due: int = 3) -> int:
        """
        Send reminders for bills approaching due date.
        
        Args:
            cluster: Cluster object
            days_before_due: Number of days before due date to send reminder
            
        Returns:
            int: Number of reminders sent
        """
        reminder_date = timezone.now() + timezone.timedelta(days=days_before_due)
        
        bills_to_remind = Bill.objects.filter(
            cluster=cluster,
            due_date__date=reminder_date.date(),
            status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
        )
        
        count = 0
        for bill in bills_to_remind:
            if BillNotificationManager.send_bill_reminder(bill):
                count += 1
        
        logger.info(f"Sent {count} bill reminders in cluster {cluster.id}")
        
        return count
    
    @staticmethod
    def acknowledge_bill(bill: Bill, acknowledged_by: str) -> bool:
        """
        Acknowledge a bill.
        
        Args:
            bill: Bill to acknowledge
            acknowledged_by: ID of the user acknowledging the bill
            
        Returns:
            bool: True if acknowledgment was successful
        """
        if bill.acknowledge(acknowledged_by):
            logger.info(f"Bill {bill.bill_number} acknowledged by user {acknowledged_by}")
            
            # Send acknowledgment confirmation
            BillNotificationManager.send_bill_acknowledged_notification(bill)
            
            return True
        return False
    
    @staticmethod
    def dispute_bill(bill: Bill, disputed_by: str, reason: str) -> bool:
        """
        Dispute a bill.
        
        Args:
            bill: Bill to dispute
            disputed_by: ID of the user disputing the bill
            reason: Reason for dispute
            
        Returns:
            bool: True if dispute was successful
        """
        if bill.dispute(disputed_by, reason):
            logger.info(f"Bill {bill.bill_number} disputed by user {disputed_by}: {reason}")
            
            # Send dispute notification to admins
            BillNotificationManager.send_bill_disputed_notification(bill)
            
            return True
        return False


class BillNotificationManager:
    """
    Manager for handling bill-related notifications.
    """
    
    @staticmethod
    def send_cluster_wide_bill_notification(bill: Bill) -> bool:
        """
        Send notification to all cluster members when an cluster-wide bill is created.
        
        Args:
            bill: Estate-wide bill object
            
        Returns:
            bool: True if notifications were sent successfully
        """
        try:
            from accounts.models import AccountUser
            
            # Get all users in the cluster
            cluster_users = AccountUser.objects.filter(
                cluster=bill.cluster,
                is_active=True
            ).iterator()
            
            if not cluster_users.exists():
                logger.warning(f"No active users found for cluster {bill.cluster.name}")
                return False


            for batch in cluster_users.iterator(chunk_size=100):
                NotificationManager.send(
                    event=NotificationEvents.PAYMENT_DUE,
                    recipients=list(batch),  # Pass the current batch of users
                    cluster=bill.cluster,
                    context={
                        'bill_number': bill.bill_number,
                        'bill_title': bill.title,
                        'bill_amount': bill.amount,
                        'currency': bill.currency,
                        'due_date': bill.due_date.strftime('%Y-%m-%d'),
                        'bill_type': bill.get_type_display(),
                        'description': bill.description or '',
                        'cluster_name': bill.cluster.name,
                        'is_cluster_wide': True,
                    }
                )
                logger.info(f"Estate-wide bill notification sent to {cluster_users.count()} users")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send cluster-wide bill notification: {e}")
            return False
    
    @staticmethod
    def send_user_specific_bill_notification(bill: Bill) -> bool:
        """
        Send notification to a specific user when a user-specific bill is created.
        
        Args:
            bill: User-specific bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                logger.warning(f"No user found for bill {bill.bill_number}")
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_DUE,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.amount,
                    'currency': bill.currency,
                    'due_date': bill.due_date.strftime('%Y-%m-%d'),
                    'bill_type': bill.get_type_display(),
                    'description': bill.description or '',
                    'is_user_specific': True,
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send user-specific bill notification: {e}")
            return False
    
    @staticmethod
    def send_new_bill_notification(bill: Bill) -> bool:
        """
        Send notification when a new bill is created.
        
        Args:
            bill: Bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                logger.warning(f"No user found for bill {bill.bill_number}")
                return False

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_DUE,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.amount,
                    'currency': bill.currency,
                    'due_date': bill.due_date.strftime('%Y-%m-%d'),
                    'bill_type': bill.get_type_display(),
                    'description': bill.description or '',
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send new bill notification: {e}")
            return False
    
    @staticmethod
    def send_bill_reminder(bill: Bill) -> bool:
        """
        Send bill payment reminder.
        
        Args:
            bill: Bill object
            
        Returns:
            bool: True if reminder was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                return False
            
            days_until_due = (bill.due_date.date() - timezone.now().date()).days
            
            NotificationManager.send(
                event=NotificationEvents.PAYMENT_DUE,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.remaining_amount,
                    'currency': bill.currency,
                    'due_date': bill.due_date.strftime('%Y-%m-%d'),
                    'days_until_due': days_until_due,
                    'bill_type': bill.get_type_display(),
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send bill reminder: {e}")
            return False
    
    @staticmethod
    def send_overdue_bill_notification(bill: Bill) -> bool:
        """
        Send notification when a bill becomes overdue.
        
        Args:
            bill: Overdue bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                return False
            
            days_overdue = (timezone.now().date() - bill.due_date.date()).days
            
            NotificationManager.send(
                event=NotificationEvents.PAYMENT_OVERDUE,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.remaining_amount,
                    'currency': bill.currency,
                    'due_date': bill.due_date.strftime('%Y-%m-%d'),
                    'days_overdue': days_overdue,
                    'bill_type': bill.get_type_display(),
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send overdue bill notification: {e}")
            return False
    
    @staticmethod
    def send_payment_confirmation(bill: Bill, transaction: Transaction) -> bool:
        """
        Send payment confirmation notification.
        
        Args:
            bill: Bill that was paid
            transaction: Payment transaction
            
        Returns:
            bool: True if confirmation was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                return False
            
            NotificationManager.send(
                event=NotificationEvents.PAYMENT_CONFIRMED,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'payment_amount': transaction.amount,
                    'currency': transaction.currency,
                    'transaction_id': transaction.transaction_id,
                    'payment_date': transaction.processed_at.strftime('%Y-%m-%d %H:%M'),
                    'remaining_amount': bill.remaining_amount,
                    'bill_status': bill.get_status_display(),
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            return False
    
    @staticmethod
    def send_bill_cancelled_notification(bill: Bill) -> bool:
        """
        Send notification when a bill is cancelled.
        
        Args:
            bill: Cancelled bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user:
                return False
            
            NotificationManager.send(
                event=NotificationEvents.BILL_CANCELLED,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.amount,
                    'currency': bill.currency,
                    'bill_type': bill.get_type_display(),
                }
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send bill cancelled notification: {e}")
            return False
    
    @staticmethod
    def send_bill_acknowledged_notification(bill: Bill) -> bool:
        """
        Send notification when a bill is acknowledged.
        
        Args:
            bill: Acknowledged bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            
            # Notify cluster admins
            cluster_admins = AccountUser.objects.filter(
                clusters=bill.cluster,
                is_cluster_admin=True
            )
            
            if cluster_admins.exists():
                NotificationManager.send(
                    event=NotificationEvents.BILL_ACKNOWLEDGED,
                    recipients=list(cluster_admins),
                    cluster=bill.cluster,
                    context={
                        'bill_number': bill.bill_number,
                        'bill_title': bill.title,
                        'bill_amount': bill.amount,
                        'currency': bill.currency,
                        'acknowledged_at': bill.acknowledged_at.strftime('%Y-%m-%d %H:%M'),
                        'user_id': str(bill.user_id),
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send bill acknowledged notification: {e}")
            return False
    
    @staticmethod
    def send_bill_disputed_notification(bill: Bill) -> bool:
        """
        Send notification when a bill is disputed.
        
        Args:
            bill: Disputed bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            from accounts.models import AccountUser
            
            # Notify cluster admins
            cluster_admins = AccountUser.objects.filter(
                clusters=bill.cluster,
                is_cluster_admin=True
            )
            
            if cluster_admins.exists():
                NotificationManager.send(
                    event=NotificationEvents.BILL_DISPUTED,
                    recipients=list(cluster_admins),
                    cluster=bill.cluster,
                    context={
                        'bill_number': bill.bill_number,
                        'bill_title': bill.title,
                        'bill_amount': bill.amount,
                        'currency': bill.currency,
                        'dispute_reason': bill.dispute_reason,
                        'disputed_at': bill.disputed_at.strftime('%Y-%m-%d %H:%M'),
                        'user_id': str(bill.user_id),
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send bill disputed notification: {e}")
            return False


# Convenience functions for common bill operations
def create_monthly_service_charge(cluster, user_id: str, amount: Decimal, 
                                 created_by: str = None) -> Bill:
    """
    Create a monthly service charge bill.
    
    Args:
        cluster: Cluster object
        user_id: User ID
        amount: Service charge amount
        created_by: ID of the user creating the bill
        
    Returns:
        Bill: Created service charge bill
    """
    from dateutil.relativedelta import relativedelta
    
    due_date = timezone.now() + relativedelta(days=30)
    
    return BillManager.create_bill(
        cluster=cluster,
        user_id=user_id,
        title=f"Monthly Service Charge - {timezone.now().strftime('%B %Y')}",
        amount=amount,
        bill_type=BillType.SERVICE_CHARGE,
        due_date=due_date,
        description="Monthly cluster service charge",
        created_by=created_by,
    )


def create_utility_bill(cluster, user_id: str, bill_type: BillType, 
                       amount: Decimal, meter_reading: str = None,
                       created_by: str = None) -> Bill:
    """
    Create a utility bill (electricity, water, etc.).
    
    Args:
        cluster: Cluster object
        user_id: User ID
        bill_type: Type of utility bill
        amount: Bill amount
        meter_reading: Meter reading (optional)
        created_by: ID of the user creating the bill
        
    Returns:
        Bill: Created utility bill
    """
    from dateutil.relativedelta import relativedelta
    
    due_date = timezone.now() + relativedelta(days=14)  # 2 weeks for utility bills
    
    metadata = {}
    if meter_reading:
        metadata['meter_reading'] = meter_reading
    
    return BillManager.create_bill(
        cluster=cluster,
        user_id=user_id,
        title=f"{bill_type.title()} Bill - {timezone.now().strftime('%B %Y')}",
        amount=amount,
        bill_type=bill_type,
        due_date=due_date,
        description=f"Monthly {bill_type.lower()} charges",
        created_by=created_by,
        metadata=metadata,
    )