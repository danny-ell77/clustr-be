"""
Cluster wallet management utilities for ClustR application.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.db.models import Sum, Q

from core.common.models.wallet import (
    Wallet,
    Transaction,
    WalletStatus,
    TransactionType,
    TransactionStatus,
)

logger = logging.getLogger('clustr')

# Special UUID for cluster wallets
CLUSTER_WALLET_USER_ID = "00000000-0000-0000-0000-000000000000"


def get_cluster_admin_for_wallet(cluster):
    """
    Get the primary cluster admin to associate with cluster wallet operations.
    
    Args:
        cluster: Cluster object
        
    Returns:
        str: Admin user ID or None if no admin found
    """
    try:
        from accounts.models import AccountUser
        
        # Get the primary cluster admin (first created admin)
        primary_admin = AccountUser.objects.filter(
            clusters=cluster,
            is_cluster_admin=True
        ).order_by('created_at').first()
        
        if primary_admin:
            return str(primary_admin.id)
        
        # Fallback to any cluster staff
        cluster_staff = AccountUser.objects.filter(
            clusters=cluster,
            is_cluster_staff=True
        ).order_by('created_at').first()
        
        if cluster_staff:
            return str(cluster_staff.id)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting cluster admin for wallet: {e}")
        return None


class ClusterWalletManager:
    """
    Manager for cluster wallet operations.
    """
    
    @staticmethod
    def get_or_create_cluster_wallet(cluster, created_by: str = None) -> Wallet:
        """
        Get or create the main wallet for a cluster.
        
        Args:
            cluster: Cluster object
            created_by: ID of the user creating the wallet
            
        Returns:
            Wallet: Cluster's main wallet
        """
        # Use special UUID for cluster wallet identification
        # but track the responsible admin in created_by/last_modified_by
        if not created_by:
            created_by = get_cluster_admin_for_wallet(cluster)
        
        wallet, created = Wallet.objects.get_or_create(
            cluster=cluster,
            user_id=CLUSTER_WALLET_USER_ID,
            defaults={
                'balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'currency': 'NGN',
                'status': WalletStatus.ACTIVE,
                'created_by': created_by,
                'last_modified_by': created_by,
            }
        )
        
        if created:
            logger.info(f"Created cluster wallet for cluster {cluster.id} by admin {created_by}")
        
        return wallet
    
    @staticmethod
    def get_cluster_wallet_balance(cluster) -> Dict[str, Any]:
        """
        Get cluster wallet balance information.
        
        Args:
            cluster: Cluster object
            
        Returns:
            Dict: Wallet balance information
        """
        try:
            wallet = Wallet.objects.get(
                cluster=cluster,
                user_id=CLUSTER_WALLET_USER_ID
            )
            
            return {
                'balance': wallet.balance,
                'available_balance': wallet.available_balance,
                'currency': wallet.currency,
                'status': wallet.status,
                'last_transaction_at': wallet.last_transaction_at,
            }
        
        except Wallet.DoesNotExist:
            return {
                'balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'currency': 'NGN',
                'status': 'not_created',
                'last_transaction_at': None,
            }
    
    @staticmethod
    def get_cluster_wallet_transactions(cluster, transaction_type: TransactionType = None,
                                      limit: int = 50) -> List[Transaction]:
        """
        Get cluster wallet transactions.
        
        Args:
            cluster: Cluster object
            transaction_type: Optional transaction type filter
            limit: Maximum number of transactions to return
            
        Returns:
            List[Transaction]: Cluster wallet transactions
        """
        try:
            wallet = Wallet.objects.get(
                cluster=cluster,
                user_id=CLUSTER_WALLET_USER_ID
            )
            
            queryset = Transaction.objects.filter(wallet=wallet)
            
            if transaction_type:
                queryset = queryset.filter(type=transaction_type)
            
            return list(queryset.order_by('-created_at')[:limit])
        
        except Wallet.DoesNotExist:
            return []
    
    @staticmethod
    def get_cluster_revenue_summary(cluster, days: int = 30) -> Dict[str, Any]:
        """
        Get cluster revenue summary from bill payments.
        
        Args:
            cluster: Cluster object
            days: Number of days to look back
            
        Returns:
            Dict: Revenue summary
        """
        try:
            wallet = Wallet.objects.get(
                cluster=cluster,
                user_id=CLUSTER_WALLET_USER_ID
            )
            
            # Get transactions from the last N days
            start_date = timezone.now() - timezone.timedelta(days=days)
            
            transactions = Transaction.objects.filter(
                wallet=wallet,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.COMPLETED,
                created_at__gte=start_date
            )
            
            # Calculate totals
            total_revenue = transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # Group by bill type from metadata
            revenue_by_type = {}
            bill_payment_count = 0
            
            for transaction in transactions:
                if transaction.metadata and transaction.metadata.get('source') == 'bill_payment':
                    bill_payment_count += 1
                    # You could extract bill type from metadata if stored
                    bill_type = transaction.metadata.get('bill_type', 'unknown')
                    if bill_type not in revenue_by_type:
                        revenue_by_type[bill_type] = Decimal('0.00')
                    revenue_by_type[bill_type] += transaction.amount
            
            return {
                'period_days': days,
                'total_revenue': total_revenue,
                'bill_payment_count': bill_payment_count,
                'revenue_by_type': revenue_by_type,
                'current_balance': wallet.balance,
                'transactions_count': transactions.count(),
            }
        
        except Wallet.DoesNotExist:
            return {
                'period_days': days,
                'total_revenue': Decimal('0.00'),
                'bill_payment_count': 0,
                'revenue_by_type': {},
                'current_balance': Decimal('0.00'),
                'transactions_count': 0,
            }
    
    @staticmethod
    def transfer_from_cluster_wallet(cluster, amount: Decimal, description: str,
                                   recipient_account: str = None, 
                                   transferred_by: str = None) -> Transaction:
        """
        Transfer funds from cluster wallet (e.g., to bank account).
        
        Args:
            cluster: Cluster object
            amount: Amount to transfer
            description: Transfer description
            recipient_account: Recipient account details
            transferred_by: ID of the user initiating transfer
            
        Returns:
            Transaction: Transfer transaction
        """
        wallet = ClusterWalletManager.get_or_create_cluster_wallet(cluster, transferred_by)
        
        if not wallet.has_sufficient_balance(amount):
            raise ValueError("Insufficient cluster wallet balance")
        
        # Create withdrawal transaction
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.WITHDRAWAL,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            metadata={
                'transfer_type': 'cluster_withdrawal',
                'recipient_account': recipient_account,
                'transferred_by': transferred_by,
            },
            created_by=transferred_by,
            last_modified_by=transferred_by,
        )
        
        # Update wallet balance
        wallet.update_balance(amount, TransactionType.WITHDRAWAL)
        
        logger.info(f"Transferred {amount} {wallet.currency} from cluster wallet")
        
        return transaction
    
    @staticmethod
    def add_manual_credit(cluster, amount: Decimal, description: str,
                         source: str = "manual", added_by: str = None) -> Transaction:
        """
        Manually add credit to cluster wallet.
        
        Args:
            cluster: Cluster object
            amount: Amount to credit
            description: Credit description
            source: Source of the credit
            added_by: ID of the user adding credit
            
        Returns:
            Transaction: Credit transaction
        """
        wallet = ClusterWalletManager.get_or_create_cluster_wallet(cluster, added_by)
        
        # Create deposit transaction
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            metadata={
                'source': source,
                'added_by': added_by,
            },
            created_by=added_by,
            last_modified_by=added_by,
        )
        
        # Update wallet balance
        wallet.update_balance(amount, TransactionType.DEPOSIT)
        
        logger.info(f"Added manual credit {amount} {wallet.currency} to cluster wallet")
        
        return transaction
    
    @staticmethod
    def get_cluster_wallet_analytics(cluster) -> Dict[str, Any]:
        """
        Get comprehensive cluster wallet analytics.
        
        Args:
            cluster: Cluster object
            
        Returns:
            Dict: Wallet analytics
        """
        try:
            wallet = Wallet.objects.get(
                cluster=cluster,
                user_id=CLUSTER_WALLET_USER_ID
            )
            
            # Get all transactions
            all_transactions = Transaction.objects.filter(wallet=wallet)
            
            # Calculate totals by type
            deposits = all_transactions.filter(
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.COMPLETED
            )
            
            withdrawals = all_transactions.filter(
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.COMPLETED
            )
            
            total_deposits = deposits.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            total_withdrawals = withdrawals.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # Bill payment specific analytics
            bill_payments = deposits.filter(
                metadata__source='bill_payment'
            )
            
            bill_payment_revenue = bill_payments.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            return {
                'current_balance': wallet.balance,
                'available_balance': wallet.available_balance,
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals,
                'net_balance': total_deposits - total_withdrawals,
                'bill_payment_revenue': bill_payment_revenue,
                'bill_payment_count': bill_payments.count(),
                'total_transactions': all_transactions.count(),
                'last_transaction_at': wallet.last_transaction_at,
                'wallet_created_at': wallet.created_at,
            }
        
        except Wallet.DoesNotExist:
            return {
                'current_balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'total_deposits': Decimal('0.00'),
                'total_withdrawals': Decimal('0.00'),
                'net_balance': Decimal('0.00'),
                'bill_payment_revenue': Decimal('0.00'),
                'bill_payment_count': 0,
                'total_transactions': 0,
                'last_transaction_at': None,
                'wallet_created_at': None,
            }


# Convenience functions
def get_cluster_balance(cluster) -> Decimal:
    """
    Get cluster wallet balance.
    
    Args:
        cluster: Cluster object
        
    Returns:
        Decimal: Current cluster wallet balance
    """
    balance_info = ClusterWalletManager.get_cluster_wallet_balance(cluster)
    return balance_info['balance']


def credit_cluster_from_bill_payment(cluster, amount: Decimal, bill, transaction=None):
    """
    Credit cluster wallet from bill payment (called automatically).
    
    Args:
        cluster: Cluster object
        amount: Amount to credit
        bill: Bill object
        transaction: Original payment transaction
    """
    try:
        # Get responsible admin for this operation
        admin_id = get_cluster_admin_for_wallet(cluster) or bill.created_by
        
        wallet = ClusterWalletManager.get_or_create_cluster_wallet(cluster, admin_id)
        
        # Create credit transaction
        cluster_transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=bill.currency,
            description=f"Bill payment credit - {bill.title}",
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            reference=transaction.transaction_id if transaction else None,
            metadata={
                'source': 'bill_payment',
                'bill_id': str(bill.id),
                'bill_number': bill.bill_number,
                'bill_type': bill.type,
                'payer_user_id': str(bill.user_id),
                'original_transaction_id': str(transaction.id) if transaction else None,
            },
            created_by=admin_id,
            last_modified_by=admin_id,
        )
        
        # Update wallet balance
        wallet.update_balance(amount, TransactionType.DEPOSIT)
        logger.info(f"Credited cluster wallet {amount} {bill.currency} from bill payment {bill.bill_number} (admin: {admin_id})")
        
        return cluster_transaction
        
    except Exception as e:
        logger.error(f"Failed to credit cluster wallet for bill {bill.bill_number}: {e}")
        return None