"""
Payment processing utilities for ClustR application.
"""

import logging
import requests
import hashlib
import hmac
import json
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.utils import timezone

from core.common.models.wallet import (
    Transaction,
    TransactionStatus,
    TransactionType,
    PaymentProvider,
)
from core.common.utils.file_storage import FileStorageManager
from core.common.utils.third_party_services import PaymentProviderFactory

logger = logging.getLogger('clustr')


class PaymentError(Exception):
    """Custom exception for payment processing errors."""
    pass


class PaymentManager:
    """
    Main payment manager for handling payment operations.
    """
    
    def initialize_payment(self, transaction: Transaction, user_email: str,
                          callback_url: str = None) -> Dict:
        """
        Initialize a payment transaction.
        
        Args:
            transaction: Transaction object
            user_email: User email address
            callback_url: Callback URL after payment
            
        Returns:
            Dict: Payment initialization response
        """
        try:
            processor = PaymentProviderFactory.get_provider(transaction.provider)
            
            if transaction.provider == PaymentProvider.PAYSTACK:
                response = processor.initialize_payment(
                    amount=transaction.amount,
                    email=user_email,
                    reference=transaction.transaction_id,
                    callback_url=callback_url,
                    metadata={
                        'transaction_id': str(transaction.id),
                        'cluster_id': str(transaction.cluster.id),
                        'user_id': str(transaction.wallet.user_id),
                    }
                )
            
            elif transaction.provider == PaymentProvider.FLUTTERWAVE:
                response = processor.initialize_payment(
                    amount=transaction.amount,
                    email=user_email,
                    tx_ref=transaction.transaction_id,
                    redirect_url=callback_url,
                    customer={
                        'email': user_email,
                        'name': 'ClustR User',
                    }
                )
            
            # Update transaction with provider response
            transaction.provider_response = response
            transaction.status = TransactionStatus.PROCESSING
            transaction.save()
            
            return response
        
        except Exception as e:
            logger.error(f"Payment initialization failed: {e}")
            # Use payment error handler for comprehensive error handling
            from core.common.utils.payment_error_utils import PaymentErrorHandler
            error_result = PaymentErrorHandler.handle_transaction_failure(transaction, str(e))
            raise PaymentError(error_result['user_message'])
    
    def verify_payment(self, transaction: Transaction) -> bool:
        """
        Verify a payment transaction.
        
        Args:
            transaction: Transaction object to verify
            
        Returns:
            bool: True if payment is successful
        """
        try:
            processor = PaymentProviderFactory.get_provider(transaction.provider)
            
            if transaction.provider == PaymentProvider.PAYSTACK:
                response = processor.verify_payment(transaction.transaction_id)
                
                if response.get('status') == 'success' and response.get('amount') == int(transaction.amount * 100):
                    transaction.provider_response = response
                    transaction.mark_as_completed()
                    self._handle_bill_payment_completion(transaction)
                    return True
                else:
                    transaction.mark_as_failed("Payment verification failed")
                    return False
            
            elif transaction.provider == PaymentProvider.FLUTTERWAVE:
                # For Flutterwave, we need the transaction ID from their response
                flw_tx_id = transaction.provider_response.get('id') if transaction.provider_response else None
                if not flw_tx_id:
                    transaction.mark_as_failed("Missing Flutterwave transaction ID")
                    return False
                
                response = processor.verify_payment(str(flw_tx_id))
                
                if (response.get('status') == 'successful' and 
                    float(response.get('amount', 0)) == float(transaction.amount)):
                    transaction.provider_response = response
                    transaction.mark_as_completed()
                    self._handle_bill_payment_completion(transaction)
                    return True
                else:
                    transaction.mark_as_failed("Payment verification failed")
                    return False
        
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            # Use payment error handler for comprehensive error handling
            from core.common.utils.payment_error_utils import PaymentErrorHandler
            PaymentErrorHandler.handle_transaction_failure(transaction, str(e))
            return False
    
    def process_webhook(self, provider: PaymentProvider, payload: str, 
                       signature: str) -> Optional[Transaction]:
        """
        Process payment webhook.
        
        Args:
            provider: Payment provider
            payload: Webhook payload
            signature: Webhook signature
            
        Returns:
            Transaction object if processed successfully
        """
        try:
            processor = PaymentProviderFactory.get_provider(provider)
            
            # Verify webhook signature
            if not processor.verify_webhook_signature(payload, signature):
                logger.warning(f"Invalid webhook signature from {provider}")
                return None
            
            data = json.loads(payload)
            
            if provider == PaymentProvider.PAYSTACK:
                event = data.get('event')
                if event == 'charge.success':
                    reference = data['data']['reference']
                    transaction = Transaction.objects.filter(transaction_id=reference).first()
                    
                    if transaction and transaction.status == TransactionStatus.PROCESSING:
                        if self.verify_payment(transaction):
                            return transaction
            
            elif provider == PaymentProvider.FLUTTERWAVE:
                event = data.get('event')
                if event == 'charge.completed':
                    tx_ref = data['data']['tx_ref']
                    transaction = Transaction.objects.filter(transaction_id=tx_ref).first()
                    
                    if transaction and transaction.status == TransactionStatus.PROCESSING:
                        if self.verify_payment(transaction):
                            return transaction
            
            return None
        
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return None
    
    def generate_receipt(self, transaction: Transaction) -> Optional[str]:
        """
        Generate a receipt for a completed transaction.
        
        Args:
            transaction: Completed transaction
            
        Returns:
            str: Receipt file URL or None if generation fails
        """
        try:
            if transaction.status != TransactionStatus.COMPLETED:
                return None
            
            # Generate receipt content
            receipt_data = {
                'transaction_id': transaction.transaction_id,
                'amount': str(transaction.amount),
                'currency': transaction.currency,
                'description': transaction.description,
                'date': transaction.processed_at.strftime('%Y-%m-%d %H:%M:%S'),
                'status': transaction.status,
                'provider': transaction.get_provider_display(),
            }
            
            # Create receipt content (simplified - in real implementation, use a template)
            receipt_content = f"""
                CLUSTR PAYMENT RECEIPT
                =====================

                Transaction ID: {receipt_data['transaction_id']}
                Amount: {receipt_data['currency']} {receipt_data['amount']}
                Description: {receipt_data['description']}
                Date: {receipt_data['date']}
                Status: {receipt_data['status']}
                Provider: {receipt_data['provider']}

                Thank you for using ClustR!
            """.strip()
            
            # Save receipt to file storage
            filename = f"receipt_{transaction.transaction_id}.txt"
            file_url = self.file_storage.save_text_file(
                content=receipt_content,
                filename=filename,
                folder="receipts"
            )
            
            # Update transaction metadata with receipt URL
            if not transaction.metadata:
                transaction.metadata = {}
            transaction.metadata['receipt_url'] = file_url
            transaction.save()
            
            return file_url
        
        except Exception as e:
            logger.error(f"Receipt generation failed: {e}")
            return None
    
    def handle_failed_payment(self, transaction: Transaction, 
                             retry_count: int = 0) -> Dict[str, Any]:
        """
        Handle failed payment with recovery options.
        
        Args:
            transaction: Failed transaction
            retry_count: Number of retry attempts
            
        Returns:
            Dict: Recovery options and information
        """
        recovery_options = {
            'can_retry': retry_count < 3,
            'alternative_providers': [],
            'support_contact': 'support@clustr.app',
            'error_message': transaction.failure_reason or 'Payment processing failed',
        }
        
        # Suggest alternative payment providers
        if transaction.provider == PaymentProvider.PAYSTACK:
            recovery_options['alternative_providers'].append(PaymentProvider.FLUTTERWAVE)
        elif transaction.provider == PaymentProvider.FLUTTERWAVE:
            recovery_options['alternative_providers'].append(PaymentProvider.PAYSTACK)
        
        # Add bank transfer as fallback
        recovery_options['alternative_providers'].append(PaymentProvider.BANK_TRANSFER)
        
        return recovery_options
    
    def create_payment_transaction(self, wallet, amount: Decimal, description: str,
                                 provider: PaymentProvider, transaction_type: TransactionType = TransactionType.DEPOSIT) -> Transaction:
        """
        Create a new payment transaction.
        
        Args:
            wallet: Wallet object
            amount: Transaction amount
            description: Transaction description
            provider: Payment provider
            transaction_type: Type of transaction
            
        Returns:
            Transaction: Created transaction object
        """
        transaction = Transaction.objects.create(
            cluster=wallet.cluster,
            wallet=wallet,
            type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            description=description,
            provider=provider,
            status=TransactionStatus.PENDING,
            created_by=wallet.created_by,
            last_modified_by=wallet.last_modified_by,
        )
        
        # Freeze amount for withdrawal/payment transactions
        if transaction_type in [TransactionType.WITHDRAWAL, TransactionType.PAYMENT, TransactionType.BILL_PAYMENT]:
            if not wallet.freeze_amount(amount):
                transaction.mark_as_failed("Insufficient balance")
                raise PaymentError("Insufficient wallet balance")
        
        return transaction
    
    def _handle_bill_payment_completion(self, transaction: Transaction):
        """
        Handle completion of direct bill payment.
        
        Args:
            transaction: Completed transaction
        """
        try:
            if (transaction.type == TransactionType.BILL_PAYMENT and 
                transaction.status == TransactionStatus.COMPLETED and
                transaction.metadata and 
                transaction.metadata.get('payment_method') == 'direct'):
                
                bill_id = transaction.metadata.get('bill_id')
                if bill_id:
                    from core.common.models import Bill
                    try:
                        bill = Bill.objects.get(id=bill_id)
                        bill.add_payment(transaction.amount, transaction)
                        logger.info(f"Direct bill payment completed: {transaction.transaction_id} for bill {bill.bill_number}")
                    except Bill.DoesNotExist:
                        logger.error(f"Bill not found for direct payment: {bill_id}")
        
        except Exception as e:
            logger.error(f"Error handling bill payment completion: {e}")


# Convenience functions for common payment operations
def initialize_deposit(wallet, amount: Decimal, provider: PaymentProvider, 
                      user_email: str, callback_url: str = None) -> Tuple[Transaction, Dict]:
    """
    Initialize a wallet deposit transaction.
    
    Args:
        wallet: Wallet object
        amount: Deposit amount
        provider: Payment provider
        user_email: User email
        callback_url: Callback URL
        
    Returns:
        Tuple: (Transaction object, Payment initialization response)
    """
    manager = PaymentManager()
    
    transaction = manager.create_payment_transaction(
        wallet=wallet,
        amount=amount,
        description=f"Wallet deposit - {amount} {wallet.currency}",
        provider=provider,
        transaction_type=TransactionType.DEPOSIT
    )
    
    response = manager.initialize_payment(transaction, user_email, callback_url)
    
    return transaction, response


def process_bill_payment(wallet, bill, provider: PaymentProvider) -> Transaction:
    """
    Process a bill payment transaction.
    
    Args:
        wallet: Wallet object
        bill: Bill object
        provider: Payment provider
        
    Returns:
        Transaction: Created transaction object
    """
    manager = PaymentManager()
    
    transaction = manager.create_payment_transaction(
        wallet=wallet,
        amount=bill.remaining_amount,
        description=f"Bill payment - {bill.title}",
        provider=provider,
        transaction_type=TransactionType.BILL_PAYMENT
    )
    
    # For wallet payments, mark as completed immediately
    if provider == PaymentProvider.CASH:  # Assuming cash means wallet balance
        transaction.mark_as_completed()
        bill.add_payment(transaction.amount, transaction)
    
    return transaction