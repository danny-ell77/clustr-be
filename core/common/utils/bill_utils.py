"""
Bill management utilities for ClustR application.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.template import Context
from django.db.models import Q, Sum

from core.common.models.wallet import (
    Bill,
    BillStatus,
    BillType,
    Transaction,
    TransactionType,
    Wallet,
)
from core.common.utils.notification_utils import NotificationManager
from core.common.email_sender import AccountEmailSender, NotificationTypes

logger = logging.getLogger('clustr')


class BillManager:
    """
    Manager for handling bill operations.
    """
    
    @staticmethod
    def create_bill(cluster, user_id: str, title: str, amount: Decimal,
                   bill_type: BillType, due_date, description: str = None,
                   created_by: str = None, metadata: Dict = None) -> Bill:
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
    def get_bills_summary(cluster, user_id: str) -> Dict[str, Any]:
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
    def process_bill_payment(bill: Bill, wallet: Wallet, amount: Decimal = None) -> Transaction:
        """
        Process payment for a bill using wallet balance.
        
        Args:
            bill: Bill to pay
            wallet: Wallet to debit
            amount: Amount to pay (defaults to remaining amount)
            
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
        
        # Update bill
        bill.add_payment(amount, transaction)
        
        logger.info(f"Bill payment processed: {transaction.transaction_id} for bill {bill.bill_number}")
        
        # Send payment confirmation
        BillNotificationManager.send_payment_confirmation(bill, transaction)
        
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
    def send_new_bill_notification(bill: Bill) -> bool:
        """
        Send notification when a new bill is created.
        
        Args:
            bill: Bill object
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Get user email (this would need to be implemented based on your user model)
            from accounts.models import AccountUser
            user = AccountUser.objects.filter(id=bill.user_id).first()
            
            if not user or not user.email_address:
                logger.warning(f"No email found for user {bill.user_id}")
                return False
            
            context = Context({
                'user_name': user.name,
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'bill_amount': bill.amount,
                'currency': bill.currency,
                'due_date': bill.due_date.strftime('%Y-%m-%d'),
                'bill_type': bill.get_type_display(),
                'description': bill.description or '',
            })
            
            sender = AccountEmailSender(
                recipients=[user.email_address],
                email_type=NotificationTypes.BILL_REMINDER,  # We'll use this for new bills too
                context=context
            )
            
            return sender.send()
        
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
            
            if not user or not user.email_address:
                return False
            
            days_until_due = (bill.due_date.date() - timezone.now().date()).days
            
            context = Context({
                'user_name': user.name,
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'bill_amount': bill.remaining_amount,
                'currency': bill.currency,
                'due_date': bill.due_date.strftime('%Y-%m-%d'),
                'days_until_due': days_until_due,
                'bill_type': bill.get_type_display(),
            })
            
            sender = AccountEmailSender(
                recipients=[user.email_address],
                email_type=NotificationTypes.BILL_REMINDER,
                context=context
            )
            
            return sender.send()
        
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
            
            if not user or not user.email_address:
                return False
            
            days_overdue = (timezone.now().date() - bill.due_date.date()).days
            
            context = Context({
                'user_name': user.name,
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'bill_amount': bill.remaining_amount,
                'currency': bill.currency,
                'due_date': bill.due_date.strftime('%Y-%m-%d'),
                'days_overdue': days_overdue,
                'bill_type': bill.get_type_display(),
            })
            
            sender = AccountEmailSender(
                recipients=[user.email_address],
                email_type=NotificationTypes.BILL_REMINDER,  # Would need OVERDUE_BILL type
                context=context
            )
            
            return sender.send()
        
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
            
            if not user or not user.email_address:
                return False
            
            context = Context({
                'user_name': user.name,
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'payment_amount': transaction.amount,
                'currency': transaction.currency,
                'transaction_id': transaction.transaction_id,
                'payment_date': transaction.processed_at.strftime('%Y-%m-%d %H:%M'),
                'remaining_amount': bill.remaining_amount,
                'bill_status': bill.get_status_display(),
            })
            
            sender = AccountEmailSender(
                recipients=[user.email_address],
                email_type=NotificationTypes.PAYMENT_RECEIPT,
                context=context
            )
            
            return sender.send()
        
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
            
            if not user or not user.email_address:
                return False
            
            context = Context({
                'user_name': user.name,
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'bill_amount': bill.amount,
                'currency': bill.currency,
                'bill_type': bill.get_type_display(),
            })
            
            sender = AccountEmailSender(
                recipients=[user.email_address],
                email_type=NotificationTypes.BILL_REMINDER,  # Would need BILL_CANCELLED type
                context=context
            )
            
            return sender.send()
        
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
            
            admin_emails = [admin.email_address for admin in cluster_admins if admin.email_address]
            
            if admin_emails:
                context = Context({
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.amount,
                    'currency': bill.currency,
                    'acknowledged_at': bill.acknowledged_at.strftime('%Y-%m-%d %H:%M'),
                    'user_id': str(bill.user_id),
                })
                
                sender = AccountEmailSender(
                    recipients=admin_emails,
                    email_type=NotificationTypes.BILL_REMINDER,  # Would need BILL_ACKNOWLEDGED type
                    context=context
                )
                
                return sender.send()
            
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
            
            admin_emails = [admin.email_address for admin in cluster_admins if admin.email_address]
            
            if admin_emails:
                context = Context({
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': bill.amount,
                    'currency': bill.currency,
                    'dispute_reason': bill.dispute_reason,
                    'disputed_at': bill.disputed_at.strftime('%Y-%m-%d %H:%M'),
                    'user_id': str(bill.user_id),
                })
                
                sender = AccountEmailSender(
                    recipients=admin_emails,
                    email_type=NotificationTypes.BILL_REMINDER,  # Would need BILL_DISPUTED type
                    context=context
                )
                
                return sender.send()
            
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
        description="Monthly estate service charge",
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