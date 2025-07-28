"""
Payment management views for ClustR management app.
"""

import logging
from decimal import Decimal
from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from accounts.permissions import HasSpecificPermission
from core.common.permissions import PaymentsPermissions
from core.common.models import (
    Wallet,
    Transaction,
    Bill,
    RecurringPayment,
    BillStatus,
    TransactionStatus,
)
from core.common.utils import (
    BillManager,
    RecurringPaymentManager,
)
from core.common.utils.cluster_wallet_utils import ClusterWalletManager
from core.common.utils.third_party_services import PaymentProviderFactory, PaymentProviderError
from core.common.responses import success_response, error_response
from core.common.serializers.payment_serializers import (
    PaymentDashboardSerializer,
    CreateBillSerializer,
    BulkBillsSerializer,
    BillListResponseSerializer,
    BillSerializer,
    TransactionListResponseSerializer,
    TransactionSerializer,
    RecurringPaymentListResponseSerializer,
    RecurringPaymentSerializer,
    UpdateBillStatusSerializer,
    PauseRecurringPaymentSerializer,
    ClusterWalletResponseSerializer,
    ClusterWalletTransferSerializer,
    ClusterWalletCreditSerializer,
    PaymentErrorSerializer,
)

logger = logging.getLogger("clustr")


class PaymentManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for payment management operations (admin/staff only).
    """

    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission(
            [
                PaymentsPermissions.ManageWallet,
                PaymentsPermissions.ManageBill,
                PaymentsPermissions.ManageTransaction,
            ]
        ),
    ]

    @action(detail=False, methods=["get"])
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
            total_recurring_payments = RecurringPayment.objects.filter(
                cluster=cluster
            ).count()

            # Get financial summary
            completed_transactions = Transaction.objects.filter(
                cluster=cluster, status=TransactionStatus.COMPLETED
            )

            total_transaction_volume = completed_transactions.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")

            pending_bills = Bill.objects.filter(
                cluster=cluster,
                status__in=[BillStatus.PENDING, BillStatus.PARTIALLY_PAID],
            )

            total_pending_bills_amount = pending_bills.aggregate(
                total=Sum("amount") - Sum("paid_amount")
            )["total"] or Decimal("0.00")

            # Get recent activity
            recent_transactions = Transaction.objects.filter(cluster=cluster).order_by(
                "-created_at"
            )[:10]

            recent_bills = Bill.objects.filter(cluster=cluster).order_by("-created_at")[
                :10
            ]

            # Get cluster wallet information
            cluster_wallet_info = ClusterWalletManager.get_cluster_wallet_balance(
                cluster
            )
            cluster_revenue = ClusterWalletManager.get_cluster_revenue_summary(
                cluster, days=30
            )

            dashboard_data = {
                "statistics": {
                    "total_wallets": total_wallets,
                    "total_transactions": total_transactions,
                    "total_bills": total_bills,
                    "total_recurring_payments": total_recurring_payments,
                    "total_transaction_volume": total_transaction_volume,
                    "total_pending_bills_amount": total_pending_bills_amount,
                },
                "cluster_wallet": {
                    "balance": cluster_wallet_info["balance"],
                    "available_balance": cluster_wallet_info["available_balance"],
                    "currency": cluster_wallet_info["currency"],
                    "status": cluster_wallet_info["status"],
                    "last_transaction_at": cluster_wallet_info["last_transaction_at"],
                },
                "cluster_revenue": {
                    "period_days": cluster_revenue["period_days"],
                    "total_revenue": cluster_revenue["total_revenue"],
                    "bill_payment_count": cluster_revenue["bill_payment_count"],
                    "current_balance": cluster_revenue["current_balance"],
                    "transactions_count": cluster_revenue["transactions_count"],
                },
                "recent_transactions": TransactionSerializer(
                    recent_transactions, many=True
                ).data,
                "recent_bills": BillSerializer(recent_bills, many=True).data,
            }

            serializer = PaymentDashboardSerializer(data=dashboard_data)
            serializer.is_valid(raise_exception=True)

            return success_response(
                data=serializer.validated_data,
                message="Payment dashboard data retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving payment dashboard: {e}")
            return error_response(
                message="Failed to retrieve payment dashboard",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def create_bill(self, request):
        """
        Create a new bill for a user.
        """
        try:
            cluster = request.cluster_context
            serializer = CreateBillSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            # Create bill
            bill = BillManager.create_bill(
                cluster=cluster,
                user_id=data["user_id"],
                title=data["title"],
                amount=data["amount"],
                bill_type=data["type"],
                due_date=data["due_date"],
                description=data.get("description"),
                created_by=str(request.user.id),
                metadata=data.get("metadata", {}),
            )

            response_serializer = BillSerializer(bill)

            return success_response(
                data=response_serializer.data,
                message="Bill created successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating bill: {e}")
            return error_response(
                message="Failed to create bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def create_bulk_bills(self, request):
        """
        Create multiple bills at once.
        """
        try:
            cluster = request.cluster_context
            serializer = BulkBillsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            bills_data = serializer.validated_data["bills"]

            # Process bills data
            processed_bills = []
            for bill_data in bills_data:
                processed_bills.append(
                    {
                        "user_id": bill_data["user_id"],
                        "title": bill_data["title"],
                        "amount": bill_data["amount"],
                        "type": bill_data["type"],
                        "due_date": bill_data["due_date"],
                        "description": bill_data.get("description"),
                        "metadata": bill_data.get("metadata", {}),
                    }
                )

            # Create bills
            created_bills = BillManager.create_bulk_bills(
                cluster=cluster,
                user_bills=processed_bills,
                created_by=str(request.user.id),
            )

            response_data = {
                "created_count": len(created_bills),
                "requested_count": len(bills_data),
                "bills": BillSerializer(created_bills, many=True).data,
            }

            return success_response(
                data=response_data,
                message=f"Created {len(created_bills)} out of {len(bills_data)} bills",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating bulk bills: {e}")
            return error_response(
                message="Failed to create bulk bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def bills(self, request):
        """
        Get bills with filtering and pagination.
        """
        try:
            cluster = request.cluster_context

            # Get query parameters
            user_id = request.query_params.get("user_id")
            status_filter = request.query_params.get("status")
            bill_type = request.query_params.get("type")

            # Build queryset
            queryset = Bill.objects.filter(cluster=cluster)

            if user_id:
                queryset = queryset.filter(user_id=user_id)

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            if bill_type:
                queryset = queryset.filter(type=bill_type)

            queryset = queryset.order_by("-created_at")

            # Apply pagination
            paginator = PageNumberPagination()
            paginated_bills = paginator.paginate_queryset(queryset, request)

            serializer = BillSerializer(paginated_bills, many=True)

            response_data = {
                "bills": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.page_size,
                    "total_count": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                },
            }

            response_serializer = BillListResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return success_response(
                data=response_serializer.validated_data,
                message="Bills retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving bills: {e}")
            return error_response(
                message="Failed to retrieve bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        """
        Get transactions with filtering and pagination.
        """
        try:
            cluster = request.cluster_context

            # Get query parameters
            user_id = request.query_params.get("user_id")
            transaction_type = request.query_params.get("type")
            status_filter = request.query_params.get("status")

            # Build queryset
            queryset = Transaction.objects.filter(cluster=cluster)

            if user_id:
                queryset = queryset.filter(wallet__user_id=user_id)

            if transaction_type:
                queryset = queryset.filter(type=transaction_type)

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            queryset = queryset.order_by("-created_at")

            # Apply pagination
            paginator = PageNumberPagination()
            paginated_transactions = paginator.paginate_queryset(queryset, request)

            serializer = TransactionSerializer(paginated_transactions, many=True)

            response_data = {
                "transactions": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.page_size,
                    "total_count": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                },
            }

            response_serializer = TransactionListResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return success_response(
                data=response_serializer.validated_data,
                message="Transactions retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving transactions: {e}")
            return error_response(
                message="Failed to retrieve transactions",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def recurring_payments(self, request):
        """
        Get recurring payments with filtering and pagination.
        """
        try:
            cluster = request.cluster_context

            # Get query parameters
            user_id = request.query_params.get("user_id")
            status_filter = request.query_params.get("status")

            # Build queryset
            queryset = RecurringPayment.objects.filter(cluster=cluster)

            if user_id:
                queryset = queryset.filter(user_id=user_id)

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            queryset = queryset.order_by("-created_at")

            # Apply pagination
            paginator = PageNumberPagination()
            paginated_payments = paginator.paginate_queryset(queryset, request)

            serializer = RecurringPaymentSerializer(paginated_payments, many=True)

            response_data = {
                "recurring_payments": serializer.data,
                "pagination": {
                    "page": paginator.page.number,
                    "page_size": paginator.page_size,
                    "total_count": paginator.page.paginator.count,
                    "total_pages": paginator.page.paginator.num_pages,
                },
            }

            response_serializer = RecurringPaymentListResponseSerializer(
                data=response_data
            )
            response_serializer.is_valid(raise_exception=True)

            return success_response(
                data=response_serializer.validated_data,
                message="Recurring payments retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving recurring payments: {e}")
            return error_response(
                message="Failed to retrieve recurring payments",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def update_bill_status(self, request):
        """
        Update bill status.
        """
        try:
            cluster = request.cluster_context
            serializer = UpdateBillStatusSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data
            bill_id = data["bill_id"]
            new_status = data["status"]

            # Get bill
            try:
                bill = Bill.objects.get(id=bill_id, cluster=cluster)
            except Bill.DoesNotExist:
                return error_response(
                    message="Bill not found", status_code=status.HTTP_404_NOT_FOUND
                )

            # Update status
            BillManager.update_bill_status(
                bill=bill, new_status=new_status, updated_by=str(request.user.id)
            )

            response_serializer = BillSerializer(bill)

            return success_response(
                data=response_serializer.data,
                message="Bill status updated successfully",
            )

        except Exception as e:
            logger.error(f"Error updating bill status: {e}")
            return error_response(
                message="Failed to update bill status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def pause_recurring_payment(self, request):
        """
        Pause a recurring payment.
        """
        try:
            cluster = request.cluster_context
            serializer = PauseRecurringPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payment_id = serializer.validated_data["payment_id"]

            # Get recurring payment
            try:
                payment = RecurringPayment.objects.get(id=payment_id, cluster=cluster)
            except RecurringPayment.DoesNotExist:
                return error_response(
                    message="Recurring payment not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # Pause payment
            success = RecurringPaymentManager.pause_recurring_payment(
                payment=payment, paused_by=str(request.user.id)
            )

            if success:
                response_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=response_serializer.data,
                    message="Recurring payment paused successfully",
                )
            else:
                return error_response(
                    message="Cannot pause recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error pausing recurring payment: {e}")
            return error_response(
                message="Failed to pause recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
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

            response_data = {
                "analytics": analytics,
                "recent_transactions": TransactionSerializer(
                    recent_transactions, many=True
                ).data,
            }

            response_serializer = ClusterWalletResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return success_response(
                data=response_serializer.validated_data,
                message="Cluster wallet information retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving cluster wallet information: {e}")
            return error_response(
                message="Failed to retrieve cluster wallet information",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def cluster_wallet_transfer(self, request):
        """
        Transfer funds from cluster wallet with payment provider integration.
        """
        try:
            cluster = request.cluster_context
            serializer = ClusterWalletTransferSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            # Validate recipient account details
            recipient_account = data.get("recipient_account")
            if not recipient_account:
                return error_response(
                    message="Recipient account details are required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            required_fields = ["account_number", "bank_code", "account_name"]
            missing_fields = [field for field in required_fields if not recipient_account.get(field)]
            if missing_fields:
                return error_response(
                    message=f"Missing recipient account fields: {', '.join(missing_fields)}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Determine payment provider
            provider = data.get("provider", "paystack")

            # Process transfer with payment provider integration
            transaction = ClusterWalletManager.transfer_from_cluster_wallet(
                cluster=cluster,
                amount=data["amount"],
                description=data["description"],
                recipient_account=recipient_account,
                transferred_by=str(request.user.id),
                provider=provider,
            )

            response_data = {
                "transaction_id": transaction.transaction_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "description": transaction.description,
                "status": transaction.status,
                "processed_at": transaction.processed_at,
                "reference": transaction.reference,
                "recipient_account": {
                    "account_number": recipient_account["account_number"],
                    "account_name": transaction.metadata.get("verified_account_name") if transaction.metadata else recipient_account["account_name"],
                    "bank_code": recipient_account["bank_code"],
                },
            }

            return success_response(
                data=response_data,
                message="Cluster wallet transfer completed successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return error_response(
                message=str(e), 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PaymentProviderError as e:
            logger.error(f"Payment provider error processing cluster wallet transfer: {e}")
            return error_response(
                message=f"Payment provider error: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error(f"Error processing cluster wallet transfer: {e}")
            return error_response(
                message="Failed to process cluster wallet transfer",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def verify_manual_credit(self, request):
        """
        Verify a manual credit payment through payment provider.
        """
        try:
            cluster = request.cluster_context
            transaction_id = request.data.get("transaction_id")
            
            if not transaction_id:
                return error_response(
                    message="Transaction ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Get transaction
            try:
                transaction = Transaction.objects.get(
                    transaction_id=transaction_id,
                    cluster=cluster,
                    type=TransactionType.DEPOSIT
                )
            except Transaction.DoesNotExist:
                return error_response(
                    message="Transaction not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # Verify payment
            success = ClusterWalletManager.verify_manual_credit_payment(transaction)
            
            if success:
                response_data = {
                    "transaction_id": transaction.transaction_id,
                    "status": transaction.status,
                    "amount": transaction.amount,
                    "processed_at": transaction.processed_at,
                    "verified": True,
                }
                
                return success_response(
                    data=response_data,
                    message="Manual credit payment verified successfully",
                )
            else:
                return error_response(
                    message="Payment verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error verifying manual credit payment: {e}")
            return error_response(
                message="Failed to verify manual credit payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def retry_failed_payment(self, request):
        """
        Retry a failed payment transaction.
        """
        try:
            from core.common.models.wallet import PaymentError
            from core.common.utils.payment_error_utils import retry_failed_payment
            
            cluster = request.cluster_context
            error_id = request.data.get("error_id")
            
            if not error_id:
                return error_response(
                    message="Payment error ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Get payment error
            try:
                payment_error = PaymentError.objects.get(
                    id=error_id,
                    cluster=cluster
                )
            except PaymentError.DoesNotExist:
                return error_response(
                    message="Payment error not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # Retry payment
            success, message = retry_failed_payment(payment_error)
            
            if success:
                response_data = {
                    "error_id": payment_error.id,
                    "transaction_id": payment_error.transaction.transaction_id,
                    "retry_count": payment_error.retry_count,
                    "status": payment_error.transaction.status,
                }
                
                return success_response(
                    data=response_data,
                    message=message,
                )
            else:
                return error_response(
                    message=message,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error retrying failed payment: {e}")
            return error_response(
                message="Failed to retry payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def available_payment_providers(self, request):
        """
        Get list of available payment providers.
        """
        try:
            available_providers = PaymentProviderFactory.get_available_providers()
            
            response_data = {
                "providers": [
                    {
                        "code": provider,
                        "name": provider.replace('_', ' ').title(),
                        "available": True,
                    }
                    for provider in available_providers
                ]
            }
            
            return success_response(
                data=response_data,
                message="Available payment providers retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving available payment providers: {e}")
            return error_response(
                message="Failed to retrieve available payment providers",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def cluster_wallet_credit(self, request):
        """
        Manually add credit to cluster wallet with payment provider integration.
        """
        try:
            cluster = request.cluster_context
            serializer = ClusterWalletCreditSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data

            # Determine payment provider
            provider = data.get("provider", "bank_transfer")
            
            # Add credit with payment provider integration
            transaction = ClusterWalletManager.add_manual_credit(
                cluster=cluster,
                amount=data["amount"],
                description=data["description"],
                source=data["source"],
                added_by=str(request.user.id),
                provider=provider,
            )

            response_data = {
                "transaction_id": transaction.transaction_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "description": transaction.description,
                "status": transaction.status,
                "processed_at": transaction.processed_at,
                "payment_url": transaction.metadata.get("payment_url") if transaction.metadata else None,
                "reference": transaction.reference,
                "requires_verification": transaction.metadata.get("requires_verification", False) if transaction.metadata else False,
            }

            message = "Cluster wallet credit initiated successfully"
            if transaction.metadata and transaction.metadata.get("payment_url"):
                message += ". Please complete payment using the provided URL."

            return success_response(
                data=response_data,
                message=message,
                status_code=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return error_response(
                message=str(e), 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PaymentProviderError as e:
            logger.error(f"Payment provider error adding cluster wallet credit: {e}")
            return error_response(
                message=f"Payment provider error: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error(f"Error adding cluster wallet credit: {e}")
            return error_response(
                message="Failed to add cluster wallet credit",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
