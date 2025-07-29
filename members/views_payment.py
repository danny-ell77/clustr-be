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
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import HasSpecificPermission
from core.common.permissions import PaymentsPermissions
from core.common.decorators import audit_viewset
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
from core.common.serializers.payment_serializers import (
    WalletBalanceResponseSerializer,
    WalletDepositSerializer,
    DepositResponseSerializer,
    TransactionSerializer,
    TransactionListResponseSerializer,
    BillSerializer,
    BillListResponseSerializer,
    BillAcknowledgeSerializer,
    BillDisputeSerializer,
    BillPaymentSerializer,
    BillPaymentResponseSerializer,
    DirectBillPaymentSerializer,
    RecurringPaymentSerializer,
    RecurringPaymentListResponseSerializer,
    CreateRecurringPaymentSerializer,
    PauseRecurringPaymentSerializer,
    PaginationSerializer,
)
from core.common.utils import (
    BillManager,
    RecurringPaymentManager,
    PaymentManager,
    initialize_deposit,
    process_bill_payment,
)
from core.common.responses import success_response, error_response
from members.filters import TransactionFilter, BillFilter, RecurringPaymentFilter

logger = logging.getLogger('clustr')


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for payment views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@audit_viewset(resource_type="wallet")
class WalletViewSet(viewsets.ViewSet):
    """
    ViewSet for wallet operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet])
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter
    
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
            
            # Serialize the response
            serializer = WalletBalanceResponseSerializer({
                'balance': wallet.balance,
                'available_balance': wallet.available_balance,
                'currency': wallet.currency,
                'status': wallet.status,
                'is_pin_set': wallet.is_pin_set,
                'last_transaction_at': wallet.last_transaction_at,
            })
            
            return success_response(
                data=serializer.data,
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
            
            # Validate input data
            serializer = WalletDepositSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            amount = validated_data['amount']
            provider = validated_data['provider']
            callback_url = validated_data.get('callback_url')
            
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
                callback_url=callback_url
            )
            
            # Serialize the response
            response_serializer = DepositResponseSerializer({
                'transaction_id': transaction.transaction_id,
                'amount': transaction.amount,
                'currency': transaction.currency,
                'provider': transaction.provider,
                'payment_url': payment_response.get('authorization_url') or payment_response.get('link'),
                'reference': payment_response.get('reference') or payment_response.get('tx_ref'),
            })
            
            return success_response(
                data=response_serializer.data,
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
        Get user's transaction history with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Get wallet
            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                # Return empty response with proper serialization
                empty_response = TransactionListResponseSerializer({
                    'transactions': [],
                    'pagination': {
                        'page': 1,
                        'page_size': 20,
                        'total_count': 0,
                        'total_pages': 0,
                    }
                })
                return success_response(
                    data=empty_response.data,
                    message="No transactions found"
                )
            
            # Build queryset
            queryset = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
            
            # Apply filters
            filterset = TransactionFilter(request.GET, queryset=queryset, request=request)
            if filterset.is_valid():
                queryset = filterset.qs
            
            # Apply pagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            # Serialize transactions
            transaction_serializer = TransactionSerializer(page, many=True)
            
            # Prepare pagination data
            pagination_data = {
                'page': paginator.page.number,
                'page_size': paginator.page_size,
                'total_count': paginator.page.paginator.count,
                'total_pages': paginator.page.paginator.num_pages,
            }
            
            # Serialize the complete response
            response_serializer = TransactionListResponseSerializer({
                'transactions': transaction_serializer.data,
                'pagination': pagination_data
            })
            
            return success_response(
                data=response_serializer.data,
                message="Transactions retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving transactions: {e}")
            return error_response(
                message="Failed to retrieve transactions",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@audit_viewset(resource_type="bill")
class BillViewSet(viewsets.ViewSet):
    """
    ViewSet for bill operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewBill])
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = BillFilter
    
    @action(detail=False, methods=['get'])
    def my_bills(self, request):
        """
        Get user's bills with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Build queryset
            queryset = Bill.objects.filter(cluster=cluster, user_id=user_id).order_by('-created_at')
            
            # Apply filters
            filterset = BillFilter(request.GET, queryset=queryset, request=request)
            if filterset.is_valid():
                queryset = filterset.qs
            
            # Apply pagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            # Serialize bills
            bill_serializer = BillSerializer(page, many=True)
            
            # Prepare pagination data
            pagination_data = {
                'page': paginator.page.number,
                'page_size': paginator.page_size,
                'total_count': paginator.page.paginator.count,
                'total_pages': paginator.page.paginator.num_pages,
            }
            
            # Serialize the complete response
            response_serializer = BillListResponseSerializer({
                'bills': bill_serializer.data,
                'pagination': pagination_data
            })
            
            return success_response(
                data=response_serializer.data,
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
            
            # Validate input data
            serializer = BillAcknowledgeSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            bill_id = serializer.validated_data['bill_id']
            
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
                # Serialize the response
                bill_serializer = BillSerializer(bill)
                return success_response(
                    data=bill_serializer.data,
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
            
            # Validate input data
            serializer = BillDisputeSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            bill_id = validated_data['bill_id']
            reason = validated_data['reason']
            
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
                # Serialize the response
                bill_serializer = BillSerializer(bill)
                return success_response(
                    data=bill_serializer.data,
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
            
            # Validate input data
            serializer = BillPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            bill_id = validated_data['bill_id']
            amount = validated_data.get('amount')
            
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
            transaction = BillManager.process_bill_payment(
                bill=bill,
                wallet=wallet,
                amount=amount
            )
            
            # Serialize the response
            response_serializer = BillPaymentResponseSerializer({
                'transaction_id': transaction.transaction_id,
                'amount': transaction.amount,
                'bill_id': bill.id,
                'bill_status': bill.status,
                'remaining_amount': bill.remaining_amount,
                'wallet_balance': wallet.balance,
            })
            
            return success_response(
                data=response_serializer.data,
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
            
            # Validate input data
            serializer = DirectBillPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            validated_data = serializer.validated_data
            bill_id = validated_data['bill_id']
            provider = validated_data['provider']
            amount = validated_data.get('amount')
            callback_url = validated_data.get('callback_url')
            
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
            if amount is None:
                amount = bill.remaining_amount
            elif amount > bill.remaining_amount:
                return error_response(
                    message="Payment amount exceeds remaining bill amount",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
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
                callback_url=callback_url
            )
            
            # Serialize the response
            response_serializer = DepositResponseSerializer({
                'transaction_id': transaction.transaction_id,
                'amount': amount,
                'currency': transaction.currency,
                'provider': transaction.provider,
                'payment_url': payment_response.get('authorization_url') or payment_response.get('link'),
                'reference': payment_response.get('reference') or payment_response.get('tx_ref'),
            })
            
            return success_response(
                data=response_serializer.data,
                message="Direct bill payment initialized successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error initializing direct bill payment: {e}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@audit_viewset(resource_type="recurring_payment")
class RecurringPaymentViewSet(viewsets.ViewSet):
    """
    ViewSet for recurring payment operations (residents).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet])
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringPaymentFilter
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """
        Get user's recurring payments with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Build queryset
            queryset = RecurringPayment.objects.filter(cluster=cluster, user_id=user_id).order_by('-created_at')
            
            # Apply filters
            filterset = RecurringPaymentFilter(request.GET, queryset=queryset, request=request)
            if filterset.is_valid():
                queryset = filterset.qs
            
            # Apply pagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            # Serialize recurring payments
            payment_serializer = RecurringPaymentSerializer(page, many=True)
            
            # Prepare pagination data
            pagination_data = {
                'page': paginator.page.number,
                'page_size': paginator.page_size,
                'total_count': paginator.page.paginator.count,
                'total_pages': paginator.page.paginator.num_pages,
            }
            
            # Serialize the complete response
            response_serializer = RecurringPaymentListResponseSerializer({
                'recurring_payments': payment_serializer.data,
                'pagination': pagination_data
            })
            
            return success_response(
                data=response_serializer.data,
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
    
    def create(self, request):
        """
        Create a new recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            
            # Validate input data
            serializer = CreateRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
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
                title=validated_data['title'],
                amount=validated_data['amount'],
                frequency=validated_data['frequency'],
                start_date=validated_data['start_date'],
                end_date=validated_data.get('end_date'),
                description=validated_data.get('description'),
                metadata=validated_data.get('metadata', {}),
                created_by=user_id,
            )
            
            # Serialize the response
            payment_serializer = RecurringPaymentSerializer(payment)
            
            return success_response(
                data=payment_serializer.data,
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
            
            # Validate input data
            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            payment_id = serializer.validated_data['payment_id']
            
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
                # Serialize the response
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
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
            
            # Validate input data
            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            payment_id = serializer.validated_data['payment_id']
            
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
                # Serialize the response
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
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
            
            # Validate input data
            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            payment_id = serializer.validated_data['payment_id']
            
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
                # Serialize the response
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
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