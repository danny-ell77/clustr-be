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

from accounts.permissions import HasSpecificPermission, IsClusterStaffOrAdmin
from core.common.permissions import PaymentsPermissions
from core.common.models import (
    Wallet,
    Transaction,
    Bill,
    RecurringPayment,
    BillStatus,
    TransactionStatus,
    TransactionType,
    PaymentError,
)
from core.common.models import UtilityProvider
from members.filters import RecurringPaymentFilter
from core.common.includes.third_party_services import (
    PaymentProviderFactory,
    PaymentProviderError,
)
from core.common.responses import success_response, error_response
from core.common.error_codes import CommonAPIErrorCodes
from core.common.includes.payment_error import retry_failed_payment
from core.common.includes import bills, recurring_payments, cluster_wallet
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
    UpdateRecurringPaymentSerializer,
    CreateRecurringPaymentSerializer,
    ResumeRecurringPaymentSerializer,
    CancelRecurringPaymentSerializer,
    ClusterWalletResponseSerializer,
    ClusterWalletTransferSerializer,
    ClusterWalletCreditSerializer,
)
from django.shortcuts import get_object_or_404

logger = logging.getLogger("clustr")


class PaymentManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for payment management operations (admin/staff only).
    """
    queryset = Transaction.objects.none()

    permission_classes = [
        IsAuthenticated,
        IsClusterStaffOrAdmin,
        HasSpecificPermission.check_permissions(
            for_view=[
                PaymentsPermissions.ManageWallet,
                PaymentsPermissions.ManageBill,
                PaymentsPermissions.ManageTransaction,
            ],
            for_object=[
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
                paid_at__isnull=True,
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
            cluster_wallet_info = cluster_wallet.get_wallet_balance(cluster)
            cluster_revenue = cluster_wallet.get_revenue_summary(cluster, days=30)

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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve payment dashboard",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def create_bill(self, request):
        """
        Create a new bill - supports both cluster-wide and user-specific bills.
        """
        try:
            cluster = request.cluster_context
            serializer = CreateBillSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = serializer.validated_data
            user_id = data.get("user_id")

            # Create cluster-wide or user-specific bill based on user_id
            if user_id is None:
                # Create cluster-wide bill
                bill = bills.create_cluster_wide(
                    cluster=cluster,
                    title=data["title"],
                    amount=data["amount"],
                    bill_type=data["type"],
                    due_date=data["due_date"],
                    description=data.get("description"),
                    allow_payment_after_due=data.get("allow_payment_after_due", True),
                    created_by=str(request.user.id),
                    metadata=data.get("metadata", {}),
                )
                logger.info(
                    f"Cluster-wide bill created: {bill.bill_number} by admin {request.user.id}"
                )
            else:
                # Create user-specific bill
                bill = bills.create_user_specific(
                    cluster=cluster,
                    user_id=str(user_id),
                    title=data["title"],
                    amount=data["amount"],
                    bill_type=data["type"],
                    due_date=data["due_date"],
                    description=data.get("description"),
                    allow_payment_after_due=data.get("allow_payment_after_due", True),
                    created_by=str(request.user.id),
                    metadata=data.get("metadata", {}),
                )
                logger.info(
                    f"User-specific bill created: {bill.bill_number} for user {user_id} by admin {request.user.id}"
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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to create bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def create_bulk_bills(self, request):
        """
        Create multiple bills at once - supports both cluster-wide and user-specific bills.
        """
        try:
            cluster = request.cluster_context
            serializer = BulkBillsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            bills_data = serializer.validated_data["bills"]
            created_bills = []

            for bill_data in bills_data:
                try:
                    user_id = bill_data.get("user_id")

                    if user_id is None:
                        # Create cluster-wide bill
                        bill = bills.create_cluster_wide(
                            cluster=cluster,
                            title=bill_data["title"],
                            amount=bill_data["amount"],
                            bill_type=bill_data["type"],
                            due_date=bill_data["due_date"],
                            description=bill_data.get("description"),
                            allow_payment_after_due=bill_data.get(
                                "allow_payment_after_due", True
                            ),
                            created_by=str(request.user.id),
                            metadata=bill_data.get("metadata", {}),
                        )
                    else:
                        # Create user-specific bill
                        bill = bills.create_user_specific(
                            cluster=cluster,
                            user_id=str(user_id),
                            title=bill_data["title"],
                            amount=bill_data["amount"],
                            bill_type=bill_data["type"],
                            due_date=bill_data["due_date"],
                            description=bill_data.get("description"),
                            allow_payment_after_due=bill_data.get(
                                "allow_payment_after_due", True
                            ),
                            created_by=str(request.user.id),
                            metadata=bill_data.get("metadata", {}),
                        )

                    created_bills.append(bill)

                except Exception as e:
                    logger.error(
                        f"Failed to create bill: {bill_data.get('title', 'Unknown')} - {e}"
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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to create bulk bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def bills(self, request):
        """
        Get bills with filtering and pagination.
        Supports filtering by user_id, bill_type, and cluster_wide status.
        """
        try:
            cluster = request.cluster_context

            user_id = request.query_params.get("user_id")
            bill_type = request.query_params.get("type")
            is_cluster_wide = request.query_params.get("cluster_wide")

            queryset = Bill.objects.filter(cluster=cluster)

            # Filter by user_id (supports both specific user and cluster-wide)
            if user_id:
                if user_id.lower() == "null" or user_id.lower() == "none":
                    # Show only cluster-wide bills
                    queryset = queryset.filter(user_id__isnull=True)
                else:
                    # Show bills for specific user
                    queryset = queryset.filter(user_id=user_id)

            # Filter by cluster-wide status
            if is_cluster_wide is not None:
                if is_cluster_wide.lower() in ["true", "1", "yes"]:
                    queryset = queryset.filter(user_id__isnull=True)
                elif is_cluster_wide.lower() in ["false", "0", "no"]:
                    queryset = queryset.filter(user_id__isnull=False)

            if bill_type:
                queryset = queryset.filter(type=bill_type)

            # Add prefetch for acknowledged_by to optimize queries
            queryset = queryset.prefetch_related("acknowledged_by").order_by(
                "-created_at"
            )

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

            # response_serializer = BillListResponseSerializer(data=response_data)
            # response_serializer.is_valid(raise_exception=True)

            return success_response(
                data=response_data,
                message="Bills retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving bills: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path=r"bills/(?P<bill_id>[^/.]+)")
    def bill_detail(self, request, bill_id=None):
        """
        Get a single bill by ID.
        """
        try:
            cluster = request.cluster_context
            bill = get_object_or_404(Bill, id=bill_id, cluster=cluster)
            serializer = BillSerializer(bill)
            
            return success_response(
                data=serializer.data,
                message="Bill retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving bill: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        """
        Get transactions with filtering and pagination.
        """
        try:
            cluster = request.cluster_context

            user_id = request.query_params.get("user_id")
            transaction_type = request.query_params.get("type")
            status_filter = request.query_params.get("status")

            queryset = Transaction.objects.filter(cluster=cluster)

            if user_id:
                queryset = queryset.filter(wallet__user_id=user_id)

            if transaction_type:
                queryset = queryset.filter(type=transaction_type)

            if status_filter:
                queryset = queryset.filter(status=status_filter)

            queryset = queryset.order_by("-created_at")

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


            return success_response(
                data=response_data,
                message="Transactions retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving transactions: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve transactions",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path=r"transactions/(?P<transaction_id>[^/.]+)")
    def transaction_detail(self, request, transaction_id=None):
        """
        Get a single transaction by ID.
        """
        try:
            cluster = request.cluster_context
            transaction = get_object_or_404(Transaction, id=transaction_id, cluster=cluster)
            serializer = TransactionSerializer(transaction)
            
            return success_response(
                data=serializer.data,
                message="Transaction retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving transaction: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve transaction",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def recurring_payments(self, request):
        """
        Get recurring payments with filtering and pagination.
        """
        try:
            cluster = request.cluster_context

            queryset = RecurringPayment.objects.filter(cluster=cluster)

            filterset = RecurringPaymentFilter(request.query_params, queryset=queryset)
            if filterset.is_valid():
                queryset = filterset.qs

            queryset = queryset.order_by("-created_at")

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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve recurring payments",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def update_bill_status(self, request):
        """
        Update bill status.
        """
        serializer = UpdateBillStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        bill = get_object_or_404(
            Bill, id=data["bill_id"], cluster=request.cluster_context
        )
        new_status = data["status"]

        bills.update_status(
            bill=bill, new_status=new_status, updated_by=str(request.user.id)
        )

        response_serializer = BillSerializer(bill)

        return success_response(
            data=response_serializer.data,
            message="Bill status updated successfully",
        )

    @action(detail=False, methods=["post"])
    def pause_recurring_payment(self, request):
        """
        Pause a recurring payment.
        """
        payment = get_object_or_404(
            RecurringPayment,
            id=request.data["payment_id"],
            cluster=request.cluster_context,
        )

        success = recurring_payments.pause(
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
                error_code=CommonAPIErrorCodes.OPERATION_NOT_ALLOWED,
                message="Cannot pause recurring payment in current status",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def create_recurring_payment(self, request):
        """
        Create a new recurring payment (admin).
        """
        try:
            cluster = request.cluster_context
            serializer = CreateRecurringPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data

            wallet = get_object_or_404(
                Wallet,
                id=validated_data["wallet_id"],
                cluster=cluster,
            )

            bill = None
            if validated_data.get("bill_id"):
                bill = get_object_or_404(
                    Bill, id=validated_data["bill_id"], cluster=cluster
                )

            utility_provider = None
            if validated_data.get("utility_provider_id"):
                utility_provider = get_object_or_404(
                    UtilityProvider,
                    id=validated_data["utility_provider_id"],
                    cluster=cluster,
                )

            payment = recurring_payments.create(
                wallet=wallet,
                title=validated_data["title"],
                amount=validated_data["amount"],
                frequency=validated_data["frequency"],
                start_date=validated_data["start_date"],
                end_date=validated_data.get("end_date"),
                description=validated_data.get("description"),
                metadata=validated_data.get("metadata", {}),
                created_by=str(request.user.id),
                bill=bill,
                utility_provider=utility_provider,
                customer_id=validated_data.get("customer_id"),
                payment_source=validated_data.get("payment_source", "wallet"),
                spending_limit=validated_data.get("spending_limit"),
            )

            response_serializer = RecurringPaymentSerializer(payment)

            return success_response(
                data=response_serializer.data,
                message="Recurring payment created successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating recurring payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to create recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["put"])
    def update_recurring_payment(self, request):
        """
        Update a recurring payment (admin).
        """
        try:
            cluster = request.cluster_context
            serializer = UpdateRecurringPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            payment_id = validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster
            )

            bill = None
            if "bill_id" in validated_data and validated_data["bill_id"]:
                bill = get_object_or_404(
                    Bill, id=validated_data["bill_id"], cluster=cluster
                )

            utility_provider = None
            if (
                "utility_provider_id" in validated_data
                and validated_data["utility_provider_id"]
            ):
                utility_provider = get_object_or_404(
                    UtilityProvider,
                    id=validated_data["utility_provider_id"],
                    cluster=cluster,
                )

            success = recurring_payments.update(
                payment=payment,
                bill=bill if "bill_id" in validated_data else None,
                title=validated_data.get("title"),
                description=validated_data.get("description"),
                amount=validated_data.get("amount"),
                frequency=validated_data.get("frequency"),
                end_date=validated_data.get("end_date"),
                utility_provider=(
                    utility_provider
                    if "utility_provider_id" in validated_data
                    else None
                ),
                customer_id=validated_data.get("customer_id"),
                spending_limit=validated_data.get("spending_limit"),
                metadata=validated_data.get("metadata"),
                updated_by=str(request.user.id),
            )

            if success:
                response_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=response_serializer.data,
                    message="Recurring payment updated successfully",
                )
            else:
                return error_response(
                    error_code=CommonAPIErrorCodes.OPERATION_NOT_ALLOWED,
                    message="Cannot update recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error updating recurring payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to update recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def resume_recurring_payment(self, request):
        """
        Resume a paused recurring payment (admin).
        """
        try:
            cluster = request.cluster_context
            serializer = ResumeRecurringPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payment_id = serializer.validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster
            )

            success = recurring_payments.resume(
                payment=payment, resumed_by=str(request.user.id)
            )

            if success:
                response_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=response_serializer.data,
                    message="Recurring payment resumed successfully",
                )
            else:
                return error_response(
                    error_code=CommonAPIErrorCodes.OPERATION_NOT_ALLOWED,
                    message="Cannot resume recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error resuming recurring payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to resume recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def cancel_recurring_payment(self, request):
        """
        Cancel a recurring payment (admin).
        """
        try:
            cluster = request.cluster_context
            serializer = CancelRecurringPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payment_id = serializer.validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster
            )

            success = recurring_payments.cancel(
                payment=payment, cancelled_by=str(request.user.id)
            )

            if success:
                response_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=response_serializer.data,
                    message="Recurring payment cancelled successfully",
                )
            else:
                return error_response(
                    error_code=CommonAPIErrorCodes.OPERATION_NOT_ALLOWED,
                    message="Recurring payment is already cancelled",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error cancelling recurring payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to cancel recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def cluster_wallet(self, request):
        """
        Get cluster wallet information and analytics.
        """
        try:
            cluster = request.cluster_context

            analytics = cluster_wallet.get_wallet_analytics(cluster)

            recent_transactions = cluster_wallet.get_wallet_transactions(
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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
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

            recipient_account = data.get("recipient_account")
            if not recipient_account:
                return error_response(
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message="Recipient account details are required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            required_fields = ["account_number", "bank_code", "account_name"]
            missing_fields = [
                field for field in required_fields if not recipient_account.get(field)
            ]
            if missing_fields:
                return error_response(
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message=f"Missing recipient account fields: {', '.join(missing_fields)}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            provider = data.get("provider", "paystack")

            transaction = cluster_wallet.transfer_from_wallet(
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
                    "account_name": (
                        transaction.metadata.get("verified_account_name")
                        if transaction.metadata
                        else recipient_account["account_name"]
                    ),
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
                error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                message=str(e), 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PaymentProviderError as e:
            logger.error(
                f"Payment provider error processing cluster wallet transfer: {e}"
            )
            return error_response(
                error_code=CommonAPIErrorCodes.PAYMENT_GATEWAY_ERROR,
                message=f"Payment provider error: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error(f"Error processing cluster wallet transfer: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
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
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message="Transaction ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            transaction = get_object_or_404(
                Transaction,
                transaction_id=transaction_id,
                cluster=cluster,
                type=TransactionType.DEPOSIT,
            )

            success = cluster_wallet.verify_manual_credit(transaction)

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
                    error_code=CommonAPIErrorCodes.PAYMENT_ERROR,
                    message="Payment verification failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error verifying manual credit payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to verify manual credit payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def retry_failed_payment(self, request):
        """
        Retry a failed payment transaction.
        """
        try:
            cluster = request.cluster_context
            error_id = request.data.get("error_id")

            if not error_id:
                return error_response(
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message="Payment error ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            payment_error = get_object_or_404(
                PaymentError, id=error_id, cluster=cluster
            )

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
                    error_code=CommonAPIErrorCodes.PAYMENT_ERROR,
                    message=message,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error retrying failed payment: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
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
                        "name": provider.replace("_", " ").title(),
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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
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

            provider = data.get("provider", "bank_transfer")

            transaction = cluster_wallet.add_manual_credit(
                cluster=cluster,
                amount=data["amount"],
                description=data["description"],
                source=data["source"],
                added_by=str(request.user.id),
                provider=provider,
            )

            serializer = TransactionSerializer(transaction)

            message = "Cluster wallet credit initiated successfully"
            if transaction.metadata and transaction.metadata.get("payment_url"):
                message += ". Please complete payment using the provided URL."

            return success_response(
                data=serializer.data,
                message=message,
                status_code=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return error_response(
                error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                message=str(e), 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PaymentProviderError as e:
            logger.error(f"Payment provider error adding cluster wallet credit: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.PAYMENT_GATEWAY_ERROR,
                message=f"Payment provider error: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error(f"Error adding cluster wallet credit: {e}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to add cluster wallet credit",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
