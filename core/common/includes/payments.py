"""
Payments utilities for ClustR application.
Refactored from PaymentManager static methods to pure functions.
"""

import logging
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from core.common.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
    PaymentProvider,
)
from core.common.includes.third_party_services import PaymentProviderFactory

logger = logging.getLogger('clustr')


class PaymentError(Exception):
    """Custom exception for payment processing errors."""
    pass


def initialize(transaction: Transaction, user_email: str, callback_url: str = None) -> Dict:
    """Initialize a payment transaction."""
    try:
        provider = PaymentProviderFactory.get_provider(transaction.payment_provider)
        
        payment_data = {
            'amount': float(transaction.amount),
            'currency': transaction.currency,
            'email': user_email,
            'reference': transaction.transaction_id,
            'callback_url': callback_url or settings.PAYMENT_CALLBACK_URL,
            'metadata': transaction.metadata or {}
        }
        
        response = provider.initialize_payment(payment_data)
        
        if response.get('status'):
            transaction.provider_reference = response.get('reference')
            transaction.payment_url = response.get('authorization_url')
            transaction.save()
            
            logger.info(f"Payment initialized: {transaction.transaction_id}")
            return response
        else:
            raise PaymentError(f"Payment initialization failed: {response.get('message')}")
            
    except Exception as e:
        logger.error(f"Payment initialization error: {e}")
        transaction.status = TransactionStatus.FAILED
        transaction.failure_reason = str(e)
        transaction.save()
        raise PaymentError(str(e))

@transaction.atomic
def process_webhook(provider: PaymentProvider, payload: str, signature: str) -> Optional[Transaction]:
    """
    Process webhook from payment provider.
    
    Args:
        provider: Payment provider (PAYSTACK, FLUTTERWAVE, etc.)
        payload: Raw webhook payload
        signature: Webhook signature for verification
        
    Returns:
        Transaction object if processed successfully, None otherwise
    """
    try:
        import json
        
        # Parse payload
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload in webhook")
            return None
        
        # Verify webhook signature
        if not _verify_provider_signature(provider, payload, signature):
            logger.error(f"Invalid webhook signature from {provider}")
            return None
        
        # Extract transaction reference based on provider
        reference = None
        event_type = None
        
        if provider == PaymentProvider.PAYSTACK:
            event_type = webhook_data.get('event')
            if event_type == 'charge.success':
                reference = webhook_data.get('data', {}).get('reference')
        elif provider == PaymentProvider.FLUTTERWAVE:
            event_type = webhook_data.get('event')
            if event_type == 'charge.completed':
                reference = webhook_data.get('data', {}).get('tx_ref')
        
        if not reference:
            logger.warning(f"No transaction reference found in {provider} webhook")
            return None
        
        # Find transaction
        try:
            transaction = Transaction.objects.get(transaction_id=reference)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found: {reference}")
            return None
        
        # Process based on event type
        if event_type in ['charge.success', 'charge.completed']:
            # Verify payment with provider
            if verify_payment(transaction, provider):
                logger.info(f"Webhook processed successfully for transaction {reference}")
                return transaction
            else:
                logger.error(f"Payment verification failed for transaction {reference}")
                return None
        else:
            logger.info(f"Ignoring webhook event: {event_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return None


@transaction.atomic
def verify_payment(transaction: Transaction, payment_provider: PaymentProvider) -> bool:
    """
    Verify payment with the payment provider.
    
    Args:
        transaction: Transaction to verify
        
    Returns:
        True if payment is verified and successful, False otherwise
    """
    try:
        provider_service = PaymentProviderFactory.get_provider(payment_provider)
        
        # Verify with provider
        verification_result = provider_service.verify_payment(
            transaction.provider_reference or transaction.transaction_id,
            float(transaction.amount)
        )
        
        if verification_result.get('status') == 'success':
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = timezone.now()
            transaction.provider_response = verification_result
            transaction.save()
            
            # Process post-payment actions (notifications, wallet updates, etc.)
            _handle_successful_payment(transaction)
            
            logger.info(f"Payment verified successfully: {transaction.transaction_id}")
            return True
        else:
            # Mark as failed
            transaction.status = TransactionStatus.FAILED
            transaction.failure_reason = verification_result.get('message', 'Payment verification failed')
            transaction.save()
            
            logger.error(f"Payment verification failed: {transaction.transaction_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        transaction.status = TransactionStatus.FAILED
        transaction.failure_reason = str(e)
        transaction.save()
        return False


# process_utility_payment function removed - use utilities.process_utility_payment instead
# The utilities module has a more comprehensive implementation with proper validation,
# bill creation, and error handling specifically designed for utility payments.


def process_recurring_payment(recurring_payment) -> Optional[Transaction]:
    """
    Process a recurring payment.
    
    Args:
        recurring_payment: RecurringPayment object
        
    Returns:
        Transaction object if successful, None otherwise
    """
    try:
        # Check wallet balance
        if not recurring_payment.wallet.has_sufficient_balance(recurring_payment.amount):
            logger.warning(f"Insufficient balance for recurring payment {recurring_payment.id}")
            return None
        
        # Create transaction
        transaction = Transaction.objects.create(
            cluster=recurring_payment.cluster,
            wallet=recurring_payment.wallet,
            type=TransactionType.RECURRING_PAYMENT,
            amount=recurring_payment.amount,
            currency=recurring_payment.currency,
            description=f"Recurring payment: {recurring_payment.title}",
            status=TransactionStatus.PENDING,
            created_by=recurring_payment.user_id,
            metadata={
                'recurring_payment_id': str(recurring_payment.id),
                'frequency': recurring_payment.frequency,
                **recurring_payment.metadata
            }
        )
        
        recurring_payment.process_payment()
        
        # Update transaction
        transaction.status = TransactionStatus.COMPLETED
        transaction.processed_at = timezone.now()
        transaction.save()
        
        logger.info(f"Recurring payment processed: {transaction.transaction_id}")
        return transaction
        
    except Exception as e:
        logger.error(f"Error processing recurring payment: {e}")
        return None


def _verify_provider_signature(provider: PaymentProvider, payload: str, signature: str) -> bool:
    """Verify webhook signature from specific payment provider."""
    try:
        if provider == PaymentProvider.PAYSTACK:
            secret_key = settings.PAYSTACK_SECRET_KEY
            expected_signature = hmac.new(
                secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
            
        elif provider == PaymentProvider.FLUTTERWAVE:
            secret_hash = settings.FLUTTERWAVE_SECRET_HASH
            return hmac.compare_digest(signature, secret_hash)
            
        else:
            logger.warning(f"Signature verification not implemented for {provider}")
            return True  # Skip verification for unknown providers
            
    except Exception as e:
        logger.error(f"Error verifying {provider} signature: {e}")
        return False


def _handle_successful_payment(transaction: Transaction):
    """Handle post-payment actions for successful payments."""
    try:
        from core.common.includes import notifications
        from core.notifications.events import NotificationEvents
        from accounts.models import AccountUser
        
        user = AccountUser.objects.get(id=transaction.created_by)

        # Handle different transaction types appropriately
        if transaction.type == TransactionType.BILL_PAYMENT:
            # For bill payments, handle completion without wallet update (already handled)
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = timezone.now()
            transaction.save(update_fields=['status', 'processed_at'])
            _handle_bill_payment_completion(transaction)
        else:
            # For deposits and other transactions, update wallet balance
            transaction.mark_as_completed()
        
        # Send payment confirmation notification
        notifications.send(
            event_name=NotificationEvents.PAYMENT_SUCCESSFUL,
            recipients=[user],
            cluster=transaction.cluster,
            context={
                'transaction_id': transaction.transaction_id,
                'amount': str(transaction.amount),
                'currency': transaction.currency,
                'description': transaction.description,
                'processed_at': transaction.processed_at.strftime('%Y-%m-%d %H:%M'),
            }
        )
        
        logger.info(f"Payment confirmation sent for transaction {transaction.transaction_id}")
        
    except Exception as e:
        logger.error(f"Error handling successful payment actions: {e}")


def _handle_bill_payment_completion(transaction: Transaction):
    """Handle completion of bill payments from direct payment (not wallet)."""
    try:
        # Get the bill from transaction metadata
        bill_id = transaction.metadata.get('bill_id')
        if not bill_id:
            logger.warning(f"No bill_id found in transaction {transaction.transaction_id} metadata")
            return
        
        from core.common.models import Bill, BillCategory
        try:
            bill = Bill.objects.get(id=bill_id)
        except Bill.DoesNotExist:
            logger.error(f"Bill {bill_id} not found for transaction {transaction.transaction_id}")
            return
        
        # Check if this is a direct payment (not from wallet)
        payment_method = transaction.metadata.get('payment_method', 'direct')
        
        if payment_method == 'direct':
            # For direct payments, we need to:
            # 1. Update the bill payment status
            # 2. Credit the cluster wallet (since no user wallet was debited)
            
            # Update bill payment status
            if bill.category == BillCategory.USER_MANAGED:
                bill.paid_amount += transaction.amount
                if bill.paid_amount >= bill.amount:
                    bill.paid_at = timezone.now()
                bill.payment_transaction = transaction
                bill.save(update_fields=["paid_amount", "paid_at", "payment_transaction"])
            
            # Credit cluster wallet for all bill payments (direct payments)
            bill.credit_cluster_wallet(transaction.amount, transaction)
            
            logger.info(f"Direct bill payment completed: {transaction.transaction_id} for bill {bill.bill_number}")
        
        # For utility bills, determine if cluster should be credited
        if bill.is_utility_bill():
            _handle_utility_bill_payment(bill, transaction)
            
    except Exception as e:
        logger.error(f"Error handling bill payment completion: {e}")


def _handle_utility_bill_payment(bill, transaction):
    """Handle utility bill payment completion."""
    try:
        # For utility bills, we need to determine if the cluster should be credited
        # This depends on whether it's a cluster-managed utility or user-managed
        
        if bill.category == BillCategory.CLUSTER_MANAGED:
            # Cluster-managed utility bills should credit the cluster
            bill.credit_cluster_wallet(transaction.amount, transaction)
            logger.info(f"Cluster credited for utility bill payment: {bill.bill_number}")
        else:
            # User-managed utility bills typically don't credit the cluster
            # The payment goes directly to the utility provider
            logger.info(f"User utility bill payment processed: {bill.bill_number}")
            
    except Exception as e:
        logger.error(f"Error handling utility bill payment: {e}")