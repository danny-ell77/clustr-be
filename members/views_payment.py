"""
Payment views for ClustR members app.
"""

import logging
from decimal import Decimal
from typing import Dict, Any
from django.utils import timezone
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasSpecificPermission
from core.common.permissions import PaymentsPermissions
from core.common.models import (
    Wallet,
    Transaction,
    Bill,
    RecurringPayment,
    WalletStatus,
    BillStatus,
    TransactionStatus,
    TransactionType,
    PaymentProvider,
    RecurringPaymentFrequency,
)
from core.common.utils import (
    BillManager,
    RecurringPaymentManager,
    PaymentManager,
    initialize_deposit,
    process_bill_payment,
)
from core.common.responses import success_response, error_response

logger = logging.getLogger('clustr')


class WalletViewSet(viewsets.ViewSet):
    """
    ViewSet for wallet operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet])
    ]
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        Get user's wallet balance.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(
                cluster=cluster,
                user_id=user_id,
                defaults={
                    'balance': Decimal('0.00'),
                    'available_balance': Decimal('0.00'),
                    'currency': 'NGN',
                    'status': WalletStatus.ACTIVE,
                    'created_by': user_id,
                    'last_modified_by': user_id,
                }
            )
            
            return success_response(
                data={
                    'balance': str(wallet.balance),
                    'available_balance': str(wallet.available_balance),
                    'currency': wallet.currency,
                    'status': wallet.status,
                    'is_pin_set': wallet.is_pin_set,
                    'last_transaction_at': wallet.last_transaction_at.isoformat() if wallet.last_transaction_at else None,
                },
                message="Wallet balance retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving wallet balance: {e}")
            return error_response(
                message="Failed to retrieve wallet balance",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """
        Initialize a wallet deposit.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            data = request.data
            
            # Validate required fields
            amount = data.get('amount')
            provider = data.get('provider', PaymentProvider.PAYSTACK)
            
            if not amount:
                return error_response(
                    message="Amount is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                amount = Decimal(str(amount))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except (ValueError, TypeError):
                return error_response(
                    message="Invalid amount",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(
                cluster=cluster,
                user_id=user_id,
                defaults={
                    'balance': Decimal('0.00'),
                    'available_balance': Decimal('0.00'),
                    'currency': 'NGN',
                    'status': WalletStatus.ACTIVE,
                    'created_by': user_id,
                    'last_modified_by': user_id,
                }
            )
            
            # Initialize deposit
            transaction, payment_response = initialize_deposit(
                wallet=wallet,
                amount=amount,
                provider=provider,
                user_email=request.user.email_address,
                callback_url=data.get('callback_url')
            )
            
            return success_response(
                data={
                    'transaction_id': transaction.transaction_id,
                    'amount': str(transaction.amount),
                    'currency': transaction.currency,
                    'provider': transaction.provider,
                    'payment_url': payment_response.get('authorization_url') or payment_response.get('link'),
                    'reference': payment_response.get('reference') or payment_response.get('tx_ref'),
                },
                message="Deposit initialized successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error initializing deposit: {e}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """
        Get user's transaction history.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Get query parameters
            transaction_type = request.query_params.get('type')
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Get wallet
            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                return success_response(
                    data={'transactions': [], 'pagination': {'page': 1, 'page_size': page_size, 'total_count': 0, 'total_pages': 0}},
                    message="No transactions found"
                )
            
            # Build queryset
            queryset = Transaction.objects.filter(wallet=wallet)
            
            if transaction_type:
                queryset = queryset.filter(type=transaction_type)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Apply pagination
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            transactions = queryset.order_by('-created_at')[start_index:end_index]
            
            return success_response(
                data={
                    'transactions': [
                        {
                            'id': str(transaction.id),
                            'transaction_id': transaction.transaction_id,
                            'type': transaction.type,
                            'amount': str(transaction.amount),
                            'currency': transaction.currency,
                            'status': transaction.status,
                            'description': transaction.description,
                            'provider': transaction.provider,
                            'created_at': transaction.created_at.isoformat(),
                            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None,
                            'failure_reason': transaction.failure_reason,
                        }
                        for transaction in transactions
                    ],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size,
                    }
                },
                message="Transactions retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving transactions: {e}")
            return error_response(
                message="Failed to retrieve transactions",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BillViewSet(viewsets.ViewSet):
    """
    ViewSet for bill operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewBill])
    ]
    
    @action(detail=False, methods=['get'])
    def my_bills(self, request):
        """
        Get user's bills.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Get query parameters
            status_filter = request.query_params.get('status')
            bill_type = request.query_params.get('type')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Get bills
            bills = BillManager.get_user_bills(
                cluster=cluster,
                user_id=user_id,
                status=status_filter,
                bill_type=bill_type,
                limit=None  # We'll handle pagination manually
            )
            
            # Apply pagination
            total_count = len(bills)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_bills = bills[start_index:end_index]
            
            return success_response(
                data={
                    'bills': [
                        {
                            'id': str(bill.id),
                            'bill_number': bill.bill_number,
                            'title': bill.title,
                            'amount': str(bill.amount),
                            'paid_amount': str(bill.paid_amount),
                            'remaining_amount': str(bill.remaining_amount),
                            'currency': bill.currency,
                            'status': bill.status,
                            'type': bill.type,
                            'due_date': bill.due_date.isoformat(),
                            'is_overdue': bill.is_overdue,
                            'description': bill.description,
                            'created_at': bill.created_at.isoformat(),
                        }
                        for bill in paginated_bills
                    ],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size,
                    }
                },
                message="Bills retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving bills: {e}")
            return error_response(
                message="Failed to retrieve bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get user's bills summary.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            summary = BillManager.get_bills_summary(cluster, user_id)
            
            return success_response(
                data=summary,
                message="Bills summary retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving bills summary: {e}")
            return error_response(
                message="Failed to retrieve bills summary",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def acknowledge_bill(self, request):
        """
        Acknowledge a bill.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            bill_id = request.data.get('bill_id')
            
            if not bill_id:
                return error_response(
                    message="Bill ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster, user_id=user_id)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Acknowledge bill
            success = BillManager.acknowledge_bill(bill, user_id)
            
            if success:
                return success_response(
                    data={
                        'id': str(bill.id),
                        'bill_number': bill.bill_number,
                        'status': bill.status,
                        'acknowledged_at': bill.acknowledged_at.isoformat(),
                    },
                    message="Bill acknowledged successfully"
                )
            else:
                return error_response(
                    message="Bill cannot be acknowledged in current status",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error acknowledging bill: {e}")
            return error_response(
                message="Failed to acknowledge bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def dispute_bill(self, request):
        """
        Dispute a bill.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            data = request.data
            
            bill_id = data.get('bill_id')
            reason = data.get('reason')
            
            if not bill_id or not reason:
                return error_response(
                    message="Bill ID and reason are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster, user_id=user_id)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Dispute bill
            success = BillManager.dispute_bill(bill, user_id, reason)
            
            if success:
                return success_response(
                    data={
                        'id': str(bill.id),
                        'bill_number': bill.bill_number,
                        'status': bill.status,
                        'dispute_reason': bill.dispute_reason,
                        'disputed_at': bill.disputed_at.isoformat(),
                    },
                    message="Bill disputed successfully"
                )
            else:
                return error_response(
                    message="Bill cannot be disputed in current status",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error disputing bill: {e}")
            return error_response(
                message="Failed to dispute bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def pay_bill(self, request):
        """
        Pay a bill using wallet balance.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            data = request.data
            
            bill_id = data.get('bill_id')
            amount = data.get('amount')  # Optional, defaults to remaining amount
            
            if not bill_id:
                return error_response(
                    message="Bill ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster, user_id=user_id)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Get wallet
            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                return error_response(
                    message="Wallet not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Process payment
            if amount:
                amount = Decimal(str(amount))
            
            transaction = BillManager.process_bill_payment(
                bill=bill,
                wallet=wallet,
                amount=amount
            )
            
            return success_response(
                data={
                    'transaction_id': transaction.transaction_id,
                    'amount': str(transaction.amount),
                    'bill_id': str(bill.id),
                    'bill_status': bill.status,
                    'remaining_amount': str(bill.remaining_amount),
                    'wallet_balance': str(wallet.balance),
                },
                message="Bill payment processed successfully"
            )
        
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing bill payment: {e}")
            return error_response(
                message="Failed to process bill payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def pay_bill_direct(self, request):
        """
        Pay a bill directly via payment provider (Paystack/Flutterwave).
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            data = request.data
            
            bill_id = data.get('bill_id')
            provider = data.get('provider', PaymentProvider.PAYSTACK)
            amount = data.get('amount')  # Optional, defaults to remaining amount
            
            if not bill_id:
                return error_response(
                    message="Bill ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster, user_id=user_id)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Check if bill can be paid
            if not bill.can_be_paid():
                return error_response(
                    message=f"Bill cannot be paid in current status: {bill.status}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine payment amount
            if amount:
                try:
                    amount = Decimal(str(amount))
                    if amount <= 0 or amount > bill.remaining_amount:
                        raise ValueError("Invalid amount")
                except (ValueError, TypeError):
                    return error_response(
                        message="Invalid payment amount",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                amount = bill.remaining_amount
            
            # Get or create user wallet for transaction tracking
            wallet, created = Wallet.objects.get_or_create(
                cluster=cluster,
                user_id=user_id,
                defaults={
                    'balance': Decimal('0.00'),
                    'available_balance': Decimal('0.00'),
                    'currency': bill.currency,
                    'status': WalletStatus.ACTIVE,
                    'created_by': user_id,
                    'last_modified_by': user_id,
                }
            )
            
            # Create payment transaction
            manager = PaymentManager()
            transaction = manager.create_payment_transaction(
                wallet=wallet,
                amount=amount,
                description=f"Direct bill payment - {bill.title}",
                provider=provider,
                transaction_type=TransactionType.BILL_PAYMENT
            )
            
            # Add bill reference to transaction metadata
            if not transaction.metadata:
                transaction.metadata = {}
            transaction.metadata.update({
                'bill_id': str(bill.id),
                'bill_number': bill.bill_number,
                'bill_type': bill.type,
                'payment_method': 'direct',
            })
            transaction.save()
            
            # Initialize payment with provider
            payment_response = manager.initialize_payment(
                transaction=transaction,
                user_email=request.user.email_address,
                callback_url=data.get('callback_url')
            )
            
            return success_response(
                data={
                    'transaction_id': transaction.transaction_id,
                    'bill_id': str(bill.id),
                    'bill_number': bill.bill_number,
                    'amount': str(amount),
                    'currency': transaction.currency,
                    'provider': transaction.provider,
                    'payment_url': payment_response.get('authorization_url') or payment_response.get('link'),
                    'reference': payment_response.get('reference') or payment_response.get('tx_ref'),
                },
                message="Direct bill payment initialized successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error initializing direct bill payment: {e}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecurringPaymentViewSet(viewsets.ViewSet):
    """
    ViewSet for recurring payment operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet])
    ]
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """
        Get user's recurring payments.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Get query parameters
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Get recurring payments
            payments = RecurringPaymentManager.get_user_recurring_payments(
                cluster=cluster,
                user_id=user_id,
                status=status_filter
            )
            
            # Apply pagination
            total_count = len(payments)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_payments = payments[start_index:end_index]
            
            return success_response(
                data={
                    'recurring_payments': [
                        {
                            'id': str(payment.id),
                            'title': payment.title,
                            'description': payment.description,
                            'amount': str(payment.amount),
                            'currency': payment.currency,
                            'frequency': payment.frequency,
                            'status': payment.status,
                            'start_date': payment.start_date.isoformat(),
                            'end_date': payment.end_date.isoformat() if payment.end_date else None,
                            'next_payment_date': payment.next_payment_date.isoformat(),
                            'last_payment_date': payment.last_payment_date.isoformat() if payment.last_payment_date else None,
                            'total_payments': payment.total_payments,
                            'failed_attempts': payment.failed_attempts,
                            'created_at': payment.created_at.isoformat(),
                        }
                        for payment in paginated_payments
                    ],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size,
                    }
                },
                message="Recurring payments retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving recurring payments: {e}")
            return error_response(
                message="Failed to retrieve recurring payments",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get user's recurring payments summary.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            summary = RecurringPaymentManager.get_recurring_payments_summary(cluster, user_id)
            
            return success_response(
                data=summary,
                message="Recurring payments summary retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving recurring payments summary: {e}")
            return error_response(
                message="Failed to retrieve recurring payments summary",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create(self, request):
        """
        Create a new recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            data = request.data
            
            # Validate required fields
            required_fields = ['title', 'amount', 'frequency', 'start_date']
            for field in required_fields:
                if field not in data:
                    return error_response(
                        message=f"Missing required field: {field}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get wallet
            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                return error_response(
                    message="Wallet not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Create recurring payment
            payment = RecurringPaymentManager.create_recurring_payment(
                wallet=wallet,
                title=data['title'],
                amount=Decimal(str(data['amount'])),
                frequency=data['frequency'],
                start_date=timezone.datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')),
                end_date=timezone.datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')) if data.get('end_date') else None,
                description=data.get('description'),
                metadata=data.get('metadata', {}),
                created_by=user_id,
            )
            
            return success_response(
                data={
                    'id': str(payment.id),
                    'title': payment.title,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'frequency': payment.frequency,
                    'status': payment.status,
                    'start_date': payment.start_date.isoformat(),
                    'next_payment_date': payment.next_payment_date.isoformat(),
                },
                message="Recurring payment created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error creating recurring payment: {e}")
            return error_response(
                message="Failed to create recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def pause(self, request):
        """
        Pause a recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            payment_id = request.data.get('payment_id')
            
            if not payment_id:
                return error_response(
                    message="Payment ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recurring payment
            try:
                payment = RecurringPayment.objects.get(
                    id=payment_id, 
                    cluster=cluster, 
                    user_id=user_id
                )
            except RecurringPayment.DoesNotExist:
                return error_response(
                    message="Recurring payment not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Pause payment
            success = RecurringPaymentManager.pause_recurring_payment(
                payment=payment,
                paused_by=user_id
            )
            
            if success:
                return success_response(
                    data={
                        'id': str(payment.id),
                        'status': payment.status,
                    },
                    message="Recurring payment paused successfully"
                )
            else:
                return error_response(
                    message="Cannot pause recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error pausing recurring payment: {e}")
            return error_response(
                message="Failed to pause recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def resume(self, request):
        """
        Resume a paused recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            payment_id = request.data.get('payment_id')
            
            if not payment_id:
                return error_response(
                    message="Payment ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recurring payment
            try:
                payment = RecurringPayment.objects.get(
                    id=payment_id, 
                    cluster=cluster, 
                    user_id=user_id
                )
            except RecurringPayment.DoesNotExist:
                return error_response(
                    message="Recurring payment not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Resume payment
            success = RecurringPaymentManager.resume_recurring_payment(
                payment=payment,
                resumed_by=user_id
            )
            
            if success:
                return success_response(
                    data={
                        'id': str(payment.id),
                        'status': payment.status,
                    },
                    message="Recurring payment resumed successfully"
                )
            else:
                return error_response(
                    message="Cannot resume recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error resuming recurring payment: {e}")
            return error_response(
                message="Failed to resume recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """
        Cancel a recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            payment_id = request.data.get('payment_id')
            
            if not payment_id:
                return error_response(
                    message="Payment ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recurring payment
            try:
                payment = RecurringPayment.objects.get(
                    id=payment_id, 
                    cluster=cluster, 
                    user_id=user_id
                )
            except RecurringPayment.DoesNotExist:
                return error_response(
                    message="Recurring payment not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Cancel payment
            success = RecurringPaymentManager.cancel_recurring_payment(
                payment=payment,
                cancelled_by=user_id
            )
            
            if success:
                return success_response(
                    data={
                        'id': str(payment.id),
                        'status': payment.status,
                    },
                    message="Recurring payment cancelled successfully"
                )
            else:
                return error_response(
                    message="Recurring payment is already cancelled",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error cancelling recurring payment: {e}")
            return error_response(
                message="Failed to cancel recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )