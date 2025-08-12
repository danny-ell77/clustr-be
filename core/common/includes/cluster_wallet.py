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
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        return {
            'balance': wallet.balance,
            'currency': wallet.currency,
            'last_updated': wallet.last_transaction_at
        }
    except Wallet.DoesNotExist:
        return {'balance': Decimal('0.00'), 'currency': 'NGN', 'last_updated': None}


def get_revenue_summary(cluster, days=30):
    """Get cluster revenue summary."""
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)
    
    transactions = Transaction.objects.filter(
        cluster=cluster,
        type=TransactionType.BILL_PAYMENT,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    total_revenue = sum(t.amount for t in transactions)
    
    return {
        'total_revenue': total_revenue,
        'transaction_count': transactions.count(),
        'period_days': days,
        'start_date': start_date,
        'end_date': end_date
    }


def get_wallet_analytics(cluster):
    """Get cluster wallet analytics."""
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        
        # Get recent transactions for the cluster wallet
        recent_transactions = Transaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:10]
        
        return {
            'current_balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'currency': wallet.currency,
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
        return {'error': 'Cluster wallet not found'}


def get_wallet_transactions(cluster, limit=20):
    """Get cluster wallet transactions."""
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
    try:
        wallet = Wallet.objects.get(cluster=cluster, user_id=cluster.id)
        
        if not wallet.has_sufficient_balance(amount):
            raise ValueError("Insufficient wallet balance")
        
        # Create transaction
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.TRANSFER,
            amount=amount,
            currency=wallet.currency,
            description=description,
            status='pending',
            created_by=created_by
        )
        
        # Debit the cluster wallet
        wallet.debit(amount, description)
        
        # Mark transaction as completed
        transaction.status = 'completed'
        transaction.processed_at = timezone.now()
        transaction.save(update_fields=['status', 'processed_at'])
        
        logger.info(f"Transfer completed: {transaction.transaction_id}")
        return transaction
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        raise


def verify_manual_credit(transaction):
    """Verify manual credit payment."""
    try:
        # Implement verification logic here
        transaction.status = 'verified'
        transaction.save()
        
        logger.info(f"Manual credit verified: {transaction.id}")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


@transaction.atomic
def add_manual_credit(cluster, amount, description, created_by):
    """Add manual credit to cluster wallet."""
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
        
        # Create transaction
        transaction = Transaction.objects.create(
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
        
        # Credit the cluster wallet
        wallet.credit(amount, description)
        
        logger.info(f"Manual credit added: {transaction.transaction_id}")
        return transaction
        
    except Exception as e:
        logger.error(f"Manual credit failed: {e}")
        raise


@transaction.atomic
def credit_cluster_from_bill_payment(cluster, amount, bill, transaction=None):
    """Credit cluster wallet from bill payment."""
    try:
        from core.common.models import WalletStatus
        
        # Get or create cluster wallet (using cluster.id as user_id)
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
        
        # Create credit transaction for cluster wallet
        credit_transaction = Transaction.objects.create(
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
                'original_transaction_id': str(transaction.id) if transaction else None
            }
        )
        
        # Credit the cluster wallet
        wallet.credit(amount, description)
        
        # Update original transaction metadata if provided
        if transaction:
            if not transaction.metadata:
                transaction.metadata = {}
            transaction.metadata.update({
                'cluster_credited': True,
                'cluster_credit_amount': str(amount),
                'cluster_credit_transaction_id': credit_transaction.transaction_id
            })
            transaction.save(update_fields=['metadata'])
        
        logger.info(f"Cluster {cluster.name} credited {amount} from bill payment: {bill.bill_number}")
        return credit_transaction
        
    except Exception as e:
        logger.error(f"Failed to credit cluster from bill payment: {e}")
        raise
