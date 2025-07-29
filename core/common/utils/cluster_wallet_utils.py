"""
Cluster wallet management utilities with payment provider integration.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings

from core.common.models.wallet import (
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
    PaymentProvider,
    Bill,
)
from core.common.utils.third_party_services import (
    PaymentProviderFactory,
    PaymentProviderError,
)
from core.common.utils.payment_error_utils import create_payment_error_record

logger = logging.getLogger('clustr')


class ClusterWalletManager:
    """
    Manager for cluster wallet operations with payment provider integration.
    """
    
    @staticmethod
    def get_cluster_wallet(cluster) -> Wallet:
        """
        Get or create the cluster's main wallet.
        
        Args:
            cluster: Cluster instance
            
        Returns:
            Wallet: Cluster's main wallet
        """
        cluster_wallet, created = Wallet.objects.get_or_create(
            cluster=cluster,
            user_id=cluster.id,  # Use cluster ID as user ID for cluster wallet
            defaults={
                'balance': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'currency': 'NGN',
                'status': 'active',
                'created_by': str(cluster.created_by) if cluster.created_by else None,
                'last_modified_by': str(cluster.last_modified_by) if cluster.last_modified_by else None,
            }
        )
        
        if created:
            logger.info(f"Created cluster wallet for {cluster.name}")
        
        return cluster_wallet
    
    @staticmethod
    def get_cluster_wallet_balance(cluster) -> dict[str, Any]:
        """
        Get cluster wallet balance information.
        
        Args:
            cluster: Cluster instance
            
        Returns:
            Dict: Wallet balance information
        """
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        return {
            'balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'currency': wallet.currency,
            'status': wallet.status,
            'last_transaction_at': wallet.last_transaction_at,
        }
    
    @staticmethod
    def get_cluster_revenue_summary(cluster, days: int = 30) -> dict[str, Any]:
        """
        Get cluster revenue summary for specified period.
        
        Args:
            cluster: Cluster instance
            days: Number of days to look back
            
        Returns:
            Dict: Revenue summary
        """
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        # Get revenue from bill payments
        bill_payments = Transaction.objects.filter(
            cluster=cluster,
            type=TransactionType.BILL_PAYMENT,
            status=TransactionStatus.COMPLETED,
            created_at__gte=start_date
        )
        
        total_revenue = bill_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        bill_payment_count = bill_payments.count()
        
        # Get all cluster wallet transactions
        cluster_transactions = Transaction.objects.filter(
            wallet=wallet,
            created_at__gte=start_date
        )
        
        return {
            'period_days': days,
            'total_revenue': total_revenue,
            'bill_payment_count': bill_payment_count,
            'current_balance': wallet.balance,
            'transactions_count': cluster_transactions.count(),
        }
    
    @staticmethod
    def get_cluster_wallet_analytics(cluster) -> dict[str, Any]:
        """
        Get comprehensive cluster wallet analytics.
        
        Args:
            cluster: Cluster instance
            
        Returns:
            Dict: Comprehensive analytics
        """
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        # Get different time period summaries
        analytics = {
            'current_balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'currency': wallet.currency,
            'status': wallet.status,
            'last_transaction_at': wallet.last_transaction_at,
            'revenue_7_days': ClusterWalletManager.get_cluster_revenue_summary(cluster, 7),
            'revenue_30_days': ClusterWalletManager.get_cluster_revenue_summary(cluster, 30),
            'revenue_90_days': ClusterWalletManager.get_cluster_revenue_summary(cluster, 90),
        }
        
        return analytics
    
    @staticmethod
    def get_cluster_wallet_transactions(cluster, limit: int = 50) -> list:
        """
        Get recent cluster wallet transactions.
        
        Args:
            cluster: Cluster instance
            limit: Maximum number of transactions to return
            
        Returns:
            list: Recent transactions
        """
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        return Transaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    @db_transaction.atomic
    def add_manual_credit(cluster, amount: Decimal, description: str, 
                         source: str, added_by: str, 
                         provider: PaymentProvider = PaymentProvider.BANK_TRANSFER) -> Transaction:
        """
        Add manual credit to cluster wallet with payment provider integration.
        
        Args:
            cluster: Cluster instance
            amount: Amount to credit
            description: Credit description
            source: Source of the credit (e.g., 'bank_transfer', 'cash_deposit')
            added_by: ID of user adding the credit
            provider: Payment provider used
            
        Returns:
            Transaction: Created transaction
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        # Create transaction record
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=wallet.currency,
            description=description,
            provider=provider,
            status=TransactionStatus.PENDING,
            metadata={
                'source': source,
                'manual_credit': True,
                'added_by': added_by,
                'requires_verification': True,
            },
            created_by=added_by,
            last_modified_by=added_by,
        )
        
        try:
            # For manual credits, we need to verify the payment through the provider
            if provider in [PaymentProvider.PAYSTACK, PaymentProvider.FLUTTERWAVE]:
                # Initialize payment for verification
                provider_instance = PaymentProviderFactory.get_provider(provider)
                
                # For manual credits, create a payment link for admin to complete
                admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@clustr.app')
                callback_url = f"{getattr(settings, 'FRONTEND_URL', '')}/admin/payments/verify/{transaction.transaction_id}"
                
                payment_result = provider_instance.initialize_payment(
                    amount=amount,
                    currency=wallet.currency,
                    email=admin_email,
                    callback_url=callback_url,
                    metadata={
                        'transaction_id': transaction.transaction_id,
                        'cluster_id': str(cluster.id),
                        'type': 'manual_credit',
                        'source': source,
                    }
                )
                
                # Update transaction with payment details
                transaction.reference = payment_result['reference']
                transaction.provider_response = payment_result
                transaction.metadata.update({
                    'payment_url': payment_result.get('authorization_url'),
                    'access_code': payment_result.get('access_code'),
                })
                transaction.save()
                
                logger.info(f"Manual credit payment initialized: {transaction.transaction_id}")
                
            else:
                # For bank transfer or cash, mark as completed immediately
                # but require admin verification
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = timezone.now()
                transaction.metadata['requires_admin_verification'] = True
                transaction.save()
                
                # Update wallet balance
                wallet.update_balance(amount, TransactionType.DEPOSIT)
                
                logger.info(f"Manual credit completed: {transaction.transaction_id}")
        
        except PaymentProviderError as e:
            # Create error record
            create_payment_error_record(transaction, str(e))
            transaction.mark_as_failed(str(e))
            raise ValueError(f"Failed to process manual credit: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing manual credit: {e}")
            transaction.mark_as_failed(str(e))
            raise ValueError(f"Failed to process manual credit: {str(e)}")
        
        return transaction
    
    @staticmethod
    @db_transaction.atomic
    def transfer_from_cluster_wallet(cluster, amount: Decimal, description: str,
                                   recipient_account: dict[str, str], transferred_by: str,
                                   provider: PaymentProvider = PaymentProvider.PAYSTACK) -> Transaction:
        """
        Transfer funds from cluster wallet with payment provider integration.
        
        Args:
            cluster: Cluster instance
            amount: Amount to transfer
            description: Transfer description
            recipient_account: dict with account details (account_number, bank_code, account_name)
            transferred_by: ID of user initiating transfer
            provider: Payment provider to use
            
        Returns:
            Transaction: Created transaction
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        if not wallet.has_sufficient_balance(amount):
            raise ValueError("Insufficient cluster wallet balance")
        
        # Freeze the amount
        if not wallet.freeze_amount(amount):
            raise ValueError("Failed to freeze transfer amount")
        
        # Create transaction record
        transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.WITHDRAWAL,
            amount=amount,
            currency=wallet.currency,
            description=description,
            provider=provider,
            status=TransactionStatus.PROCESSING,
            metadata={
                'recipient_account': recipient_account,
                'transferred_by': transferred_by,
                'transfer_type': 'cluster_withdrawal',
            },
            created_by=transferred_by,
            last_modified_by=transferred_by,
        )
        
        try:
            # Get payment provider
            provider_instance = PaymentProviderFactory.get_provider(provider)
            
            # Verify recipient account first
            account_verification = provider_instance.verify_account(
                account_number=recipient_account['account_number'],
                bank_code=recipient_account['bank_code']
            )
            
            if not account_verification['success']:
                raise PaymentProviderError("Invalid recipient account details")
            
            # Create transfer recipient
            recipient_result = provider_instance.create_transfer_recipient(
                account_number=recipient_account['account_number'],
                bank_code=recipient_account['bank_code'],
                name=recipient_account['account_name'],
                currency=wallet.currency
            )
            
            if not recipient_result['success']:
                raise PaymentProviderError("Failed to create transfer recipient")
            
            # Initiate transfer
            transfer_result = provider_instance.initiate_transfer(
                amount=amount,
                recipient_code=recipient_result['recipient_code'],
                reason=description,
                currency=wallet.currency
            )
            
            if transfer_result['success']:
                # Update transaction with transfer details
                transaction.reference = transfer_result['reference']
                transaction.provider_response = transfer_result
                transaction.metadata.update({
                    'transfer_code': transfer_result.get('transfer_code'),
                    'recipient_code': recipient_result['recipient_code'],
                    'verified_account_name': account_verification['account_name'],
                })
                
                # Mark as completed (provider will handle the actual transfer)
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = timezone.now()
                transaction.save()
                
                # Update wallet balance (amount already frozen)
                wallet.balance -= amount
                wallet.save()
                
                logger.info(f"Cluster wallet transfer completed: {transaction.transaction_id}")
                
            else:
                raise PaymentProviderError("Transfer initiation failed")
        
        except PaymentProviderError as e:
            # Unfreeze amount and create error record
            wallet.unfreeze_amount(amount)
            create_payment_error_record(transaction, str(e))
            transaction.mark_as_failed(str(e))
            raise ValueError(f"Transfer failed: {str(e)}")
        
        except Exception as e:
            # Unfreeze amount on any error
            wallet.unfreeze_amount(amount)
            logger.error(f"Error processing cluster wallet transfer: {e}")
            transaction.mark_as_failed(str(e))
            raise ValueError(f"Transfer failed: {str(e)}")
        
        return transaction
    
    @staticmethod
    def verify_manual_credit_payment(transaction: Transaction) -> bool:
        """
        Verify a manual credit payment through the payment provider.
        
        Args:
            transaction: Transaction to verify
            
        Returns:
            bool: True if payment is verified and successful
        """
        if transaction.type != TransactionType.DEPOSIT:
            return False
        
        if not transaction.reference:
            return False
        
        try:
            provider_instance = PaymentProviderFactory.get_provider(transaction.provider)
            verification_result = provider_instance.verify_payment(transaction.reference)
            
            if verification_result['success']:
                # Update transaction
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = timezone.now()
                transaction.provider_response = verification_result
                transaction.save()
                
                # Update wallet balance
                transaction.wallet.update_balance(transaction.amount, TransactionType.DEPOSIT)
                
                logger.info(f"Manual credit payment verified: {transaction.transaction_id}")
                return True
            else:
                # Payment failed
                create_payment_error_record(
                    transaction, 
                    verification_result.get('gateway_response', 'Payment verification failed')
                )
                transaction.mark_as_failed("Payment verification failed")
                return False
        
        except Exception as e:
            logger.error(f"Error verifying manual credit payment: {e}")
            create_payment_error_record(transaction, str(e))
            transaction.mark_as_failed(str(e))
            return False


def credit_cluster_from_bill_payment(cluster, amount: Decimal, bill: Bill, 
                                   transaction: Transaction = None):
    """
    Credit cluster wallet from bill payment.
    
    Args:
        cluster: Cluster instance
        amount: Amount to credit
        bill: Bill that was paid
        transaction: Payment transaction (optional)
    """
    try:
        wallet = ClusterWalletManager.get_cluster_wallet(cluster)
        
        # Create credit transaction
        credit_transaction = Transaction.objects.create(
            cluster=cluster,
            wallet=wallet,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency=wallet.currency,
            description=f"Bill payment credit: {bill.title}",
            status=TransactionStatus.COMPLETED,
            processed_at=timezone.now(),
            metadata={
                'bill_id': str(bill.id),
                'bill_number': bill.bill_number,
                'source_transaction_id': str(transaction.id) if transaction else None,
                'credit_type': 'bill_payment',
            },
            created_by=bill.created_by,
            last_modified_by=bill.last_modified_by,
        )
        
        # Update wallet balance
        wallet.update_balance(amount, TransactionType.DEPOSIT)
        
        logger.info(f"Cluster wallet credited from bill payment: {bill.bill_number}")
        
    except Exception as e:
        logger.error(f"Error crediting cluster wallet from bill payment: {e}")
        # Don't raise exception to avoid breaking bill payment flow