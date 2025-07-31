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
    BillCategory,
    Transaction,
    TransactionType,
    TransactionStatus,
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
            category=BillCategory.CLUSTER_MANAGED,
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
            category=BillCategory.USER_MANAGED,
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
    
    def get_overdue_bills_for_user(cluster, user) -> List[Bill]:
        """
        Gets all bills that are currently overdue for a specific user.

        For USER_MANAGED bills, it checks the bill's specific status.
        For CLUSTER_MANAGED bills, it uses the `is_user_overdue` method.

        Args:
            cluster: The cluster to search within.
            user: The user for whom to check overdue bills.

        Returns:
            A list of Bill objects that are overdue for the user.
        """
        user_bills = Bill.objects.filter(cluster=cluster, user_id=user.id, due_date__lt=timezone.now()).exclude(status=BillStatus.PAID)
        
        cluster_bills_query = Bill.objects.filter(cluster=cluster, category=BillCategory.CLUSTER_MANAGED, due_date__lt=timezone.now())
        
        overdue_cluster_bills = []
        for bill in cluster_bills_query:
            if bill.is_user_overdue(user):
                overdue_cluster_bills.append(bill)

        return list(user_bills) + overdue_cluster_bills
    
    def get_bills_summary(cluster, user) -> dict[str, Any]:
        """
        Get a financial summary for a user, including their share of cluster bills.

        Args:
            cluster: The cluster to search within.
            user: The user for whom to generate the summary.

        Returns:
            A dictionary containing the user's bill summary.
        """
        # User-specific bills are straightforward
        user_bills = Bill.objects.filter(cluster=cluster, user_id=user.id)
        
        # Cluster-wide bills require per-user calculation
        cluster_bills = Bill.objects.filter(cluster=cluster, category=BillCategory.CLUSTER_MANAGED)

        total_amount_due = user_bills.exclude(status=BillStatus.PAID).aggregate(
            total=Sum('amount') - Sum('paid_amount')
        )['total'] or Decimal('0.00')

        overdue_count = user_bills.filter(due_date__lt=timezone.now()).exclude(status=BillStatus.PAID).count()

        for bill in cluster_bills:
            paid_amount = bill.get_user_payment_amount(user)
            remaining = bill.amount - paid_amount
            if remaining > 0:
                total_amount_due += remaining
                if bill.due_date < timezone.now():
                    overdue_count += 1

        summary = {
            'total_bills': user_bills.count() + cluster_bills.filter(acknowledged_by=user).count(),
            'pending_bills': user_bills.filter(status=BillStatus.PENDING).count(), # Note: Pending for cluster bills is per-user
            'overdue_bills': overdue_count,
            'paid_bills': user_bills.filter(status=BillStatus.PAID).count(), # Note: Paid for cluster bills is per-user
            'total_amount_due': total_amount_due,
            'total_paid': user_bills.filter(status=BillStatus.PAID).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'), # Note: Needs adjustment for cluster bills
        }
        
        return summary
    
    def process_bill_payment(bill: Bill, wallet: Wallet, user, amount: Decimal = None) -> Transaction:
        """
        Process payment for a bill using wallet balance, deferring logic to the model.

        Args:
            bill: Bill to pay
            wallet: Wallet to debit
            user: User making the payment
            amount: Amount to pay. If None, the user's full share is assumed.

        Returns:
            Payment transaction object.
        """
        if not bill.can_be_paid_by(user):
            raise ValueError("User is not authorized to pay this bill at this time.")

        if bill.category == BillCategory.CLUSTER_MANAGED:
            paid_amount = bill.get_user_payment_amount(user)
            remaining_share = bill.amount - paid_amount
            payment_amount = amount or remaining_share
            if payment_amount > remaining_share:
                raise ValueError(f"Payment amount {payment_amount} exceeds remaining share {remaining_share}.")
        else: # User-managed bill
            remaining_amount = bill.amount - bill.paid_amount
            payment_amount = amount or remaining_amount
            if payment_amount > remaining_amount:
                raise ValueError(f"Payment amount {payment_amount} exceeds remaining amount {remaining_amount}.")

        if payment_amount <= 0:
            raise ValueError("Payment amount must be greater than 0.")

        if not wallet.has_sufficient_balance(payment_amount):
            raise ValueError("Insufficient wallet balance.")

        # Create transaction
        transaction = Transaction.objects.create(
            cluster=wallet.cluster,
            wallet=wallet,
            type=TransactionType.BILL_PAYMENT,
            amount=payment_amount,
            currency=wallet.currency,
            description=f"Bill payment: {bill.title}",
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            created_by=user.id,
            last_modified_by=user.id,
            metadata={'bill_id': str(bill.id)}
        )

        # Defer state changes to the bill model's method
        bill.add_payment(payment_amount, transaction)

        logger.info(f"Bill payment processed: {transaction.transaction_id} for bill {bill.bill_number}")

        # Send payment confirmation
        BillNotificationManager.send_payment_confirmation(bill, transaction)

        return transaction
    
    
    
    def send_bill_reminders(cluster, days_before_due: int = 3) -> int:
        """
        Send reminders for bills approaching their due date.
        For cluster bills, sends reminders to all acknowledged users who haven't paid.
        """
        reminder_date = timezone.now() + timezone.timedelta(days=days_before_due)
        bills_to_remind = Bill.objects.filter(
            cluster=cluster,
            due_date__date=reminder_date.date(),
            status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
        )

        count = 0
        for bill in bills_to_remind:
            if bill.category == BillCategory.USER_MANAGED:
                if BillNotificationManager.send_bill_reminder(bill, bill.user):
                    count += 1
            elif bill.category == BillCategory.CLUSTER_MANAGED:
                for user in bill.acknowledged_by.all():
                    if not bill.has_user_paid(user):
                        if BillNotificationManager.send_bill_reminder(bill, user):
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
            )
            
            if not cluster_users.exists():
                logger.warning(f"No active users found for cluster {bill.cluster.name}")
                return False

            # Send notifications in batches
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
    
    def send_overdue_bill_notification(bill: Bill, user, expected_amount=None) -> bool:
        """
        Send notification when a bill is overdue for a specific user.
        """
        try:
            days_overdue = (timezone.now().date() - bill.due_date.date()).days
            remaining_amount = expected_amount - bill.get_user_payment_amount(user) if expected_amount else bill.amount - bill.paid_amount

            NotificationManager.send(
                event=NotificationEvents.PAYMENT_OVERDUE,
                recipients=[user],
                cluster=bill.cluster,
                context={
                    'user_name': user.name,
                    'bill_number': bill.bill_number,
                    'bill_title': bill.title,
                    'bill_amount': remaining_amount,
                    'currency': bill.currency,
                    'due_date': bill.due_date.strftime('%Y-%m-%d'),
                    'days_overdue': days_overdue,
                    'bill_type': bill.get_type_display(),
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send overdue bill notification for bill {bill.id} to user {user.id}: {e}")
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
                        'is_disputed': bill.is_disputed,
                        'dispute_count': bill.dispute_count,
                        'user_id': str(bill.user_id),
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send bill disputed notification: {e}")
            return False
