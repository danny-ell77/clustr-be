"""
Cluster wallet utilities for ClustR application.
Refactored from WalletManager static methods to pure functions.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from core.common.models import Wallet, Transaction, TransactionType

logger = logging.getLogger('clustr')


def get_wallet_balance(cluster):
    """Get cluster wallet balance."""
    if not cluster:
        return {
            'balance': Decimal('0.00'), 
            'available_balance': Decimal('0.00'),
            'currency': 'NGN', 
            'last_transaction_at': None,
            'status': 'inactive'
        }
    
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        return {
            'balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'currency': wallet.currency,
            'last_transaction_at': wallet.last_transaction_at,
            'status': wallet.status
        }
    except Wallet.DoesNotExist:
        return {
            'balance': Decimal('0.00'), 
            'available_balance': Decimal('0.00'),
            'currency': 'NGN', 
            'last_transaction_at': None,
            'status': 'inactive'
        }


def get_revenue_summary(cluster, days=30):
    """Get cluster revenue summary."""
    if not cluster:
        return {
            'period_days': days,
            'total_revenue': Decimal('0.00'),
            'bill_payment_count': 0,
            'current_balance': Decimal('0.00'),
            'transactions_count': 0
        }
    
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)
    
    transactions = Transaction.objects.filter(
        cluster=cluster,
        type=TransactionType.BILL_PAYMENT,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    total_revenue = sum(t.amount for t in transactions)
    wallet_info = get_wallet_balance(cluster)
    
    return {
        'period_days': days,
        'total_revenue': total_revenue,
        'bill_payment_count': transactions.count(),
        'current_balance': wallet_info['balance'],
        'transactions_count': transactions.count()
    }


def get_wallet_analytics(cluster):
    """Get cluster wallet analytics."""
    if not cluster:
        raise ValueError("Cluster context is required")
    
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        
        recent_transactions = Transaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:10]
        
        return {
            'current_balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'currency': wallet.currency,
            'status': wallet.status,
            'recent_transactions': [
                {
                    'id': t.id,
                    'transaction_id': t.transaction_id,
                    'type': t.type,
                    'amount': t.amount,
                    'description': t.description,
                    'status': t.status,
                    'created_at': t.created_at
                } for t in recent_transactions
            ]
        }
    except Wallet.DoesNotExist:
        return {
            'current_balance': Decimal('0.00'),
            'available_balance': Decimal('0.00'),
            'currency': 'NGN',
            'status': 'inactive',
            'recent_transactions': []
        }


def get_wallet_transactions(cluster, limit=20):
    """Get cluster wallet transactions."""
    if not cluster:
        return Transaction.objects.none()
    
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        return Transaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:limit]
    except Wallet.DoesNotExist:
        return Transaction.objects.none()


@transaction.atomic
def transfer_from_wallet(cluster, amount, description, created_by):
    """Transfer from cluster wallet."""
    if not cluster:
        raise ValueError("Cluster context is required")
    
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        
        if not wallet.has_sufficient_balance(amount):
            raise ValueError("Insufficient wallet balance")
        
        txn = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.TRANSFER,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status='pending',
            created_by=created_by
        )
        
        wallet.debit(amount, description)
        
        txn.status = 'completed'
        txn.processed_at = timezone.now()
        txn.save(update_fields=['status', 'processed_at'])
        
        logger.info(f"Transfer completed: {txn.transaction_id}")
        return txn
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        raise


def verify_manual_credit(txn):
    """Verify manual credit payment."""
    try:
        txn.status = 'verified'
        txn.save()
        
        logger.info(f"Manual credit verified: {txn.id}")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


@transaction.atomic
def add_manual_credit(cluster, amount, description, created_by):
    """Add manual credit to cluster wallet."""
    if not cluster:
        raise ValueError("Cluster context is required")
    
    try:
        from core.common.models import WalletStatus
        
        wallet, created = Wallet.objects.get_or_create(
            cluster=cluster,
            user_id=cluster.id,
            defaults={
                'balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'currency': 'NGN',
                'status': WalletStatus.ACTIVE,
                'created_by': created_by,
                'last_modified_by': created_by
            }
        )
        
        txn = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status='completed',
            processed_at=timezone.now(),
            created_by=created_by
        )
        
        wallet.credit(amount, description)
        
        logger.info(f"Manual credit added: {txn.transaction_id}")
        return txn
        
    except Exception as e:
        logger.error(f"Manual credit failed: {e}")
        raise


@transaction.atomic
def credit_cluster_from_bill_payment(cluster, amount, bill, txn=None):
    """Credit cluster wallet from bill payment."""
    if not cluster:
        raise ValueError("Cluster context is required")
    
    try:
        from core.common.models import WalletStatus
        
        wallet, created = Wallet.objects.get_or_create(
            cluster=cluster,
            user_id=cluster.id,
            defaults={
                'balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'currency': bill.currency,
                'status': WalletStatus.ACTIVE,
                'created_by': str(cluster.id),
                'last_modified_by': str(cluster.id)
            }
        )
        
        description = f"Bill payment: {bill.title} (Bill #{bill.bill_number})"
        
        credit_txn = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status='completed',
            processed_at=timezone.now(),
            created_by=str(cluster.id),
            metadata={
                'source': 'bill_payment',
                'bill_id': str(bill.id),
                'bill_number': bill.bill_number,
                'bill_title': bill.title,
                'original_transaction_id': str(txn.id) if txn else None
            }
        )
        
        wallet.credit(amount, description)
        
        if txn:
            if not txn.metadata:
                txn.metadata = {}
            txn.metadata.update({
                'cluster_credited': True,
                'cluster_credit_amount': str(amount),
                'cluster_credit_transaction_id': credit_txn.transaction_id
            })
            txn.save(update_fields=['metadata'])
        
        logger.info(f"Cluster {cluster.name} credited {amount} from bill payment: {bill.bill_number}")
        return credit_txn
        
    except Exception as e:
        logger.error(f"Failed to credit cluster from bill payment: {e}")
        raise
