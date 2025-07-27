"""
Payment management views for ClustR management app.
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
    BillStatus,
    BillType,
    TransactionStatus,
    RecurringPaymentStatus,
)
from core.common.utils import (
    BillManager,
    RecurringPaymentManager,
    PaymentManager,
    get_payment_error_summary,
    ClusterWalletManager,
)
from core.common.responses import success_response, error_response
from core.common.serializers import build_runtime_serializer

logger = logging.getLogger('clustr')


class PaymentManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for payment management operations (admin/staff only).
    """
    
    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([
            PaymentsPermissions.ManageWallet,
            PaymentsPermissions.ManageBill,
            PaymentsPermissions.ManageTransaction,
        ])
    ]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get payment dashboard data for administrators.
        """
        try:
            cluster = request.cluster_context
            
            # Get payment statistics
            total_wallets = Wallet.objects.filter(cluster=cluster).count()
            total_transactions = Transaction.objects.filter(cluster=cluster).count()
            total_bills = Bill.objects.filter(cluster=cluster).count()
            total_recurring_payments = RecurringPayment.objects.filter(cluster=cluster).count()
            
            # Get financial summary
            completed_transactions = Transaction.objects.filter(
                cluster=cluster,
                status=TransactionStatus.COMPLETED
            )
            
            total_transaction_volume = completed_transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            pending_bills = Bill.objects.filter(
                cluster=cluster,
                status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID]
            )
            
            total_pending_bills_amount = pending_bills.aggregate(
                total=Sum('amount') - Sum('paid_amount')
            )['total'] or Decimal('0.00')
            
            # Get recent activity
            recent_transactions = Transaction.objects.filter(
                cluster=cluster
            ).order_by('-created_at')[:10]
            
            recent_bills = Bill.objects.filter(
                cluster=cluster
            ).order_by('-created_at')[:10]
            
            # Get error summary
            error_summary = get_payment_error_summary(cluster, days=7)
            
            # Get cluster wallet information
            cluster_wallet_info = ClusterWalletManager.get_cluster_wallet_balance(cluster)
            cluster_revenue = ClusterWalletManager.get_cluster_revenue_summary(cluster, days=30)
            
            dashboard_data = {
                'statistics': {
                    'total_wallets': total_wallets,
                    'total_transactions': total_transactions,
                    'total_bills': total_bills,
                    'total_recurring_payments': total_recurring_payments,
                    'total_transaction_volume': str(total_transaction_volume),
                    'total_pending_bills_amount': str(total_pending_bills_amount),
                },
                'cluster_wallet': {
                    'balance': str(cluster_wallet_info['balance']),
                    'available_balance': str(cluster_wallet_info['available_balance']),
                    'currency': cluster_wallet_info['currency'],
                    'status': cluster_wallet_info['status'],
                    'last_transaction_at': cluster_wallet_info['last_transaction_at'].isoformat() if cluster_wallet_info['last_transaction_at'] else None,
                },
                'cluster_revenue': {
                    'period_days': cluster_revenue['period_days'],
                    'total_revenue': str(cluster_revenue['total_revenue']),
                    'bill_payment_count': cluster_revenue['bill_payment_count'],
                    'current_balance': str(cluster_revenue['current_balance']),
                    'transactions_count': cluster_revenue['transactions_count'],
                },
                'recent_transactions': [
                    {
                        'id': str(t.id),
                        'transaction_id': t.transaction_id,
                        'type': t.type,
                        'amount': str(t.amount),
                        'currency': t.currency,
                        'status': t.status,
                        'created_at': t.created_at.isoformat(),
                        'user_id': str(t.wallet.user_id),
                    }
                    for t in recent_transactions
                ],
                'recent_bills': [
                    {
                        'id': str(b.id),
                        'bill_number': b.bill_number,
                        'title': b.title,
                        'amount': str(b.amount),
                        'currency': b.currency,
                        'status': b.status,
                        'due_date': b.due_date.isoformat(),
                        'user_id': str(b.user_id),
                    }
                    for b in recent_bills
                ],
                'error_summary': error_summary,
            }
            
            return success_response(
                data=dashboard_data,
                message="Payment dashboard data retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving payment dashboard: {e}")
            return error_response(
                message="Failed to retrieve payment dashboard",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_bill(self, request):
        """
        Create a new bill for a user.
        """
        try:
            cluster = request.cluster_context
            data = request.data
            
            # Validate required fields
            required_fields = ['user_id', 'title', 'amount', 'type', 'due_date']
            for field in required_fields:
                if field not in data:
                    return error_response(
                        message=f"Missing required field: {field}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create bill
            bill = BillManager.create_bill(
                cluster=cluster,
                user_id=data['user_id'],
                title=data['title'],
                amount=Decimal(str(data['amount'])),
                bill_type=data['type'],
                due_date=timezone.datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')),
                description=data.get('description'),
                created_by=str(request.user.id),
                metadata=data.get('metadata', {}),
            )
            
            return success_response(
                data={
                    'id': str(bill.id),
                    'bill_number': bill.bill_number,
                    'title': bill.title,
                    'amount': str(bill.amount),
                    'currency': bill.currency,
                    'status': bill.status,
                    'due_date': bill.due_date.isoformat(),
                    'user_id': str(bill.user_id),
                },
                message="Bill created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error creating bill: {e}")
            return error_response(
                message="Failed to create bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_bulk_bills(self, request):
        """
        Create multiple bills at once.
        """
        try:
            cluster = request.cluster_context
            bills_data = request.data.get('bills', [])
            
            if not bills_data:
                return error_response(
                    message="No bills data provided",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Process bills data
            processed_bills = []
            for bill_data in bills_data:
                processed_bills.append({
                    'user_id': bill_data['user_id'],
                    'title': bill_data['title'],
                    'amount': Decimal(str(bill_data['amount'])),
                    'type': bill_data['type'],
                    'due_date': timezone.datetime.fromisoformat(bill_data['due_date'].replace('Z', '+00:00')),
                    'description': bill_data.get('description'),
                    'metadata': bill_data.get('metadata', {}),
                })
            
            # Create bills
            created_bills = BillManager.create_bulk_bills(
                cluster=cluster,
                user_bills=processed_bills,
                created_by=str(request.user.id),
            )
            
            return success_response(
                data={
                    'created_count': len(created_bills),
                    'requested_count': len(bills_data),
                    'bills': [
                        {
                            'id': str(bill.id),
                            'bill_number': bill.bill_number,
                            'title': bill.title,
                            'amount': str(bill.amount),
                            'user_id': str(bill.user_id),
                        }
                        for bill in created_bills
                    ]
                },
                message=f"Created {len(created_bills)} out of {len(bills_data)} bills",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error creating bulk bills: {e}")
            return error_response(
                message="Failed to create bulk bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def bills(self, request):
        """
        Get bills with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            
            # Get query parameters
            user_id = request.query_params.get('user_id')
            status_filter = request.query_params.get('status')
            bill_type = request.query_params.get('type')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Build queryset
            queryset = Bill.objects.filter(cluster=cluster)
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            if bill_type:
                queryset = queryset.filter(type=bill_type)
            
            # Apply pagination
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            bills = queryset.order_by('-created_at')[start_index:end_index]
            
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
                            'user_id': str(bill.user_id),
                            'created_at': bill.created_at.isoformat(),
                        }
                        for bill in bills
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
    def transactions(self, request):
        """
        Get transactions with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            
            # Get query parameters
            user_id = request.query_params.get('user_id')
            transaction_type = request.query_params.get('type')
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Build queryset
            queryset = Transaction.objects.filter(cluster=cluster)
            
            if user_id:
                queryset = queryset.filter(wallet__user_id=user_id)
            
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
                            'user_id': str(transaction.wallet.user_id),
                            'created_at': transaction.created_at.isoformat(),
                            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None,
                            'failed_at': transaction.failed_at.isoformat() if transaction.failed_at else None,
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
    
    @action(detail=False, methods=['get'])
    def recurring_payments(self, request):
        """
        Get recurring payments with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            
            # Get query parameters
            user_id = request.query_params.get('user_id')
            status_filter = request.query_params.get('status')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Build queryset
            queryset = RecurringPayment.objects.filter(cluster=cluster)
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Apply pagination
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            payments = queryset.order_by('-created_at')[start_index:end_index]
            
            return success_response(
                data={
                    'recurring_payments': [
                        {
                            'id': str(payment.id),
                            'title': payment.title,
                            'amount': str(payment.amount),
                            'currency': payment.currency,
                            'frequency': payment.frequency,
                            'status': payment.status,
                            'start_date': payment.start_date.isoformat(),
                            'end_date': payment.end_date.isoformat() if payment.end_date else None,
                            'next_payment_date': payment.next_payment_date.isoformat(),
                            'total_payments': payment.total_payments,
                            'failed_attempts': payment.failed_attempts,
                            'user_id': str(payment.user_id),
                            'created_at': payment.created_at.isoformat(),
                        }
                        for payment in payments
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
    
    @action(detail=False, methods=['post'])
    def update_bill_status(self, request):
        """
        Update bill status.
        """
        try:
            cluster = request.cluster_context
            data = request.data
            
            bill_id = data.get('bill_id')
            new_status = data.get('status')
            
            if not bill_id or not new_status:
                return error_response(
                    message="Missing bill_id or status",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Update status
            BillManager.update_bill_status(
                bill=bill,
                new_status=new_status,
                updated_by=str(request.user.id)
            )
            
            return success_response(
                data={
                    'id': str(bill.id),
                    'bill_number': bill.bill_number,
                    'status': bill.status,
                },
                message="Bill status updated successfully"
            )
        
        except Exception as e:
            logger.error(f"Error updating bill status: {e}")
            return error_response(
                message="Failed to update bill status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def pause_recurring_payment(self, request):
        """
        Pause a recurring payment.
        """
        try:
            cluster = request.cluster_context
            payment_id = request.data.get('payment_id')
            
            if not payment_id:
                return error_response(
                    message="Missing payment_id",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recurring payment
            try:
                payment = RecurringPayment.objects.get(id=payment_id, cluster=cluster)
            except RecurringPayment.DoesNotExist:
                return error_response(
                    message="Recurring payment not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Pause payment
            success = RecurringPaymentManager.pause_recurring_payment(
                payment=payment,
                paused_by=str(request.user.id)
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
    
    @action(detail=False, methods=['get'])
    def cluster_wallet(self, request):
        """
        Get cluster wallet information and analytics.
        """
        try:
            cluster = request.cluster_context
            
            # Get comprehensive cluster wallet analytics
            analytics = ClusterWalletManager.get_cluster_wallet_analytics(cluster)
            
            # Get recent transactions
            recent_transactions = ClusterWalletManager.get_cluster_wallet_transactions(
                cluster, limit=20
            )
            
            return success_response(
                data={
                    'analytics': {
                        'current_balance': str(analytics['current_balance']),
                        'available_balance': str(analytics['available_balance']),
                        'total_deposits': str(analytics['total_deposits']),
                        'total_withdrawals': str(analytics['total_withdrawals']),
                        'net_balance': str(analytics['net_balance']),
                        'bill_payment_revenue': str(analytics['bill_payment_revenue']),
                        'bill_payment_count': analytics['bill_payment_count'],
                        'total_transactions': analytics['total_transactions'],
                        'last_transaction_at': analytics['last_transaction_at'].isoformat() if analytics['last_transaction_at'] else None,
                        'wallet_created_at': analytics['wallet_created_at'].isoformat() if analytics['wallet_created_at'] else None,
                    },
                    'recent_transactions': [
                        {
                            'id': str(t.id),
                            'transaction_id': t.transaction_id,
                            'type': t.type,
                            'amount': str(t.amount),
                            'currency': t.currency,
                            'status': t.status,
                            'description': t.description,
                            'created_at': t.created_at.isoformat(),
                            'processed_at': t.processed_at.isoformat() if t.processed_at else None,
                            'metadata': t.metadata,
                        }
                        for t in recent_transactions
                    ]
                },
                message="Cluster wallet information retrieved successfully"
            )
        
        except Exception as e:
            logger.error(f"Error retrieving cluster wallet information: {e}")
            return error_response(
                message="Failed to retrieve cluster wallet information",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def cluster_wallet_transfer(self, request):
        """
        Transfer funds from cluster wallet.
        """
        try:
            cluster = request.cluster_context
            data = request.data
            
            # Validate required fields
            amount = data.get('amount')
            description = data.get('description')
            recipient_account = data.get('recipient_account')
            
            if not amount or not description:
                return error_response(
                    message="Amount and description are required",
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
            
            # Process transfer
            transaction = ClusterWalletManager.transfer_from_cluster_wallet(
                cluster=cluster,
                amount=amount,
                description=description,
                recipient_account=recipient_account,
                transferred_by=str(request.user.id)
            )
            
            return success_response(
                data={
                    'transaction_id': transaction.transaction_id,
                    'amount': str(transaction.amount),
                    'currency': transaction.currency,
                    'description': transaction.description,
                    'status': transaction.status,
                    'processed_at': transaction.processed_at.isoformat(),
                },
                message="Cluster wallet transfer completed successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing cluster wallet transfer: {e}")
            return error_response(
                message="Failed to process cluster wallet transfer",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def cluster_wallet_credit(self, request):
        """
        Manually add credit to cluster wallet.
        """
        try:
            cluster = request.cluster_context
            data = request.data
            
            # Validate required fields
            amount = data.get('amount')
            description = data.get('description')
            source = data.get('source', 'manual')
            
            if not amount or not description:
                return error_response(
                    message="Amount and description are required",
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
            
            # Add credit
            transaction = ClusterWalletManager.add_manual_credit(
                cluster=cluster,
                amount=amount,
                description=description,
                source=source,
                added_by=str(request.user.id)
            )
            
            return success_response(
                data={
                    'transaction_id': transaction.transaction_id,
                    'amount': str(transaction.amount),
                    'currency': transaction.currency,
                    'description': transaction.description,
                    'status': transaction.status,
                    'processed_at': transaction.processed_at.isoformat(),
                },
                message="Cluster wallet credit added successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error adding cluster wallet credit: {e}")
            return error_response(
                message="Failed to add cluster wallet credit",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )