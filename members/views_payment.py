import logging
from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from accounts.permissions import HasSpecificPermission
from core.common.decorators import audit_viewset
from core.common.models import (
    Bill,
    RecurringPayment,
    Transaction,
    Wallet,
    WalletStatus,
    UtilityProvider,
    TransactionType,
    TransactionStatus,
)
from core.common.permissions import PaymentsPermissions
from core.common.responses import error_response, success_response
from core.common.serializers.payment_serializers import (
    BillAcknowledgeSerializer,
    BillDisputeModelSerializer,
    BillListResponseSerializer,
    BillPaymentResponseSerializer,
    BillPaymentSerializer,
    BillSerializer,
    CreateRecurringPaymentSerializer,
    DepositResponseSerializer,
    DirectBillPaymentSerializer,
    PauseRecurringPaymentSerializer,
    RecurringPaymentListResponseSerializer,
    RecurringPaymentSerializer,
    TransactionListResponseSerializer,
    TransactionSerializer,
    UpdateRecurringPaymentSerializer,
    WalletBalanceResponseSerializer,
    WalletDepositSerializer,
)
from core.common.includes import bills, payments, recurring_payments
from members.filters import BillFilter, RecurringPaymentFilter, TransactionFilter

logger = logging.getLogger("clustr")


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for payment views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@audit_viewset(resource_type="wallet")
class WalletViewSet(viewsets.ViewSet):
    """
    ViewSet for wallet operations (residents).
    """

    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet]),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    @action(detail=False, methods=["get"])
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
                    "balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                    "currency": "NGN",
                    "status": WalletStatus.ACTIVE,
                    "created_by": user_id,
                    "last_modified_by": user_id,
                },
            )

            serializer = WalletBalanceResponseSerializer(
                {
                    "balance": wallet.balance,
                    "available_balance": wallet.available_balance,
                    "currency": wallet.currency,
                    "status": wallet.status,
                    "is_pin_set": wallet.is_pin_set,
                    "last_transaction_at": wallet.last_transaction_at,
                }
            )

            return success_response(
                data=serializer.data, message="Wallet balance retrieved successfully"
            )

        except Exception as e:
            logger.error(f"Error retrieving wallet balance: {e}")
            return error_response(
                message="Failed to retrieve wallet balance",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def deposit(self, request):
        """
        Initialize a wallet deposit.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = WalletDepositSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            amount = validated_data["amount"]
            provider = validated_data["provider"]
            callback_url = validated_data.get("callback_url")

            wallet, created = Wallet.objects.get_or_create(
                cluster=cluster,
                user_id=user_id,
                defaults={
                    "balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                    "currency": "NGN",
                    "status": WalletStatus.ACTIVE,
                    "created_by": user_id,
                    "last_modified_by": user_id,
                },
            )

            transaction = payments.create_transaction(
                wallet=wallet,
                amount=amount,
                provider=provider,
                user_email=request.user.email_address,
                transaction_type=TransactionType.DEPOSIT,
                transaction_status=TransactionStatus.PENDING,
                callback_url=callback_url,
            )
            payment_response = payments.initialize(
                transaction=transaction,
                user_email=request.user.email_address,
                callback_url=callback_url,
            )

            response_serializer = DepositResponseSerializer(
                {
                    "transaction_id": transaction.transaction_id,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "provider": transaction.provider,
                    "payment_url": payment_response.get("authorization_url")
                    or payment_response.get("link"),
                    "reference": payment_response.get("reference")
                    or payment_response.get("tx_ref"),
                }
            )

            return success_response(
                data=response_serializer.data,
                message="Deposit initialized successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error initializing deposit: {e}")
            return error_response(
                message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        """
        Get user's transaction history with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                empty_response = TransactionListResponseSerializer(
                    {
                        "transactions": [],
                        "pagination": {
                            "page": 1,
                            "page_size": 20,
                            "total_count": 0,
                            "total_pages": 0,
                        },
                    }
                )
                return success_response(
                    data=empty_response.data, message="No transactions found"
                )

            queryset = Transaction.objects.filter(wallet=wallet).order_by("-created_at")

            filterset = TransactionFilter(
                request.GET, queryset=queryset, request=request
            )
            if filterset.is_valid():
                queryset = filterset.qs

            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)

            transaction_serializer = TransactionSerializer(page, many=True)

            pagination_data = {
                "page": paginator.page.number,
                "page_size": paginator.page_size,
                "total_count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
            }

            response_serializer = TransactionListResponseSerializer(
                {
                    "transactions": transaction_serializer.data,
                    "pagination": pagination_data,
                }
            )

            return success_response(
                data=response_serializer.data,
                message="Transactions retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving transactions: {e}")
            return error_response(
                message="Failed to retrieve transactions",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@audit_viewset(resource_type="bill")
class BillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for bill operations (residents).
    """

    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewBill]),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = BillFilter
    queryset = Bill.objects.all()

    @action(detail=False, methods=["get"], url_path="my_bills", url_name="my-bills")
    def my_bills(self, request):
        """
        Get user's bills with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            queryset = Bill.objects.filter(cluster=cluster, user_id=user_id).order_by(
                "-created_at"
            )

            filterset = BillFilter(request.GET, queryset=queryset, request=request)
            if filterset.is_valid():
                queryset = filterset.qs

            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)

            bill_serializer = BillSerializer(page, many=True)

            pagination_data = {
                "page": paginator.page.number,
                "page_size": paginator.page_size,
                "total_count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
            }

            response_serializer = BillListResponseSerializer(
                {"bills": bill_serializer.data, "pagination": pagination_data}
            )

            return success_response(
                data=response_serializer.data, message="Bills retrieved successfully"
            )

        except Exception as e:
            logger.error(f"Error retrieving bills: {e}")
            return error_response(
                message="Failed to retrieve bills",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="summary", url_name="summary")
    def summary(self, request):
        """
        Get user's bills summary.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            summary = bills.get_summary(cluster, user_id)

            return success_response(
                data=summary, message="Bills summary retrieved successfully"
            )

        except Exception as e:
            logger.error(f"Error retrieving bills summary: {e}")
            return error_response(
                message="Failed to retrieve bills summary",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="acknowledge-bill",
        url_name="acknowledge_bill",
    )
    def acknowledge_bill(self, request):
        """
        Acknowledge a bill.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            bill = self.get_object()

            serializer = BillAcknowledgeSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            bill_id = serializer.validated_data["bill_id"]

            success = bills.acknowledge(bill, user_id)

            if success:
                bill_serializer = BillSerializer(bill)
                return success_response(
                    data=bill_serializer.data, message="Bill acknowledged successfully"
                )
            else:
                return error_response(
                    message="Bill cannot be acknowledged in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error acknowledging bill: {e}")
            return error_response(
                message="Failed to acknowledge bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True, methods=["post"], url_path="dispute-bill", url_name="dispute_bill"
    )
    def dispute_bill(self, request):
        """
        Dispute a bill.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            bill = self.get_object()

            serializer = BillDisputeModelSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            bill_id = validated_data["bill_id"]
            reason = validated_data["reason"]

            success = bills.dispute(bill, user_id, reason)

            if success:
                bill_serializer = BillSerializer(bill)
                return success_response(
                    data=bill_serializer.data, message="Bill disputed successfully"
                )
            else:
                return error_response(
                    message="Bill cannot be disputed in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error disputing bill: {e}")
            return error_response(
                message="Failed to dispute bill",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="pay-bill", url_name="pay_bill")
    def pay_bill(self, request):
        """
        Pay a bill using wallet balance.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            bill = self.get_object()

            serializer = BillPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            bill_id = validated_data["bill_id"]
            amount = validated_data.get("amount")
            
            # Generate idempotency key from request headers or create one
            idempotency_key = request.headers.get('Idempotency-Key')
            if not idempotency_key:
                import uuid
                idempotency_key = f"bill_payment_{bill.id}_{user_id}_{uuid.uuid4().hex[:8]}"

            wallet = get_object_or_404(Wallet, cluster=cluster, user_id=user_id)
            transaction = bills.process_payment(
                bill=bill, wallet=wallet, amount=amount, user=request.user, idempotency_key=idempotency_key
            )

            response_serializer = BillPaymentResponseSerializer(
                {
                    "transaction_id": transaction.transaction_id,
                    "amount": transaction.amount,
                    "bill_id": bill.id,
                    "bill_status": bill.status,
                    "remaining_amount": bill.remaining_amount,
                    "wallet_balance": wallet.balance,
                }
            )

            return success_response(
                data=response_serializer.data,
                message="Bill payment processed successfully",
            )

        except ValueError as e:
            return error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing bill payment: {e}")
            return error_response(
                message="Failed to process bill payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="pay-bill-direct",
        url_name="pay_bill_direct",
    )
    def pay_bill_direct(self, request):
        """
        Pay a bill directly via payment provider (Paystack/Flutterwave).
        This is used when the cluster (estate) member does not have funds in their 
        wallet and wants to pay the bill directly.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)
            bill = self.get_object()

            serializer = DirectBillPaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            bill_id = validated_data["bill_id"]
            provider = validated_data["provider"]
            amount = validated_data.get("amount")
            callback_url = validated_data.get("callback_url")

            # Check if user can pay this bill (includes acknowledgment and due date checks)
            if not bill.can_be_paid_by(request.user):
                if not bill.acknowledged_by.filter(id=request.user.id).exists():
                    return error_response(
                        message="Bill must be acknowledged before payment",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                elif bill.is_overdue and not bill.allow_payment_after_due:
                    return error_response(
                        message="Payment not allowed after due date",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    return error_response(
                        message="You are not authorized to pay this bill",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            if not bill.can_be_paid():
                if bill.is_fully_paid:
                    return error_response(
                        message="Bill is already fully paid",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                elif bill.is_disputed:
                    return error_response(
                        message="Cannot pay disputed bill",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    return error_response(
                        message="Bill cannot be paid",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            if amount is None:
                amount = bill.remaining_amount
            elif amount > bill.remaining_amount:
                return error_response(
                    message="Payment amount exceeds remaining bill amount",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            wallet, created = Wallet.objects.get_or_create(
                cluster=cluster,
                user_id=user_id,
                defaults={
                    "balance": Decimal("0.00"),
                    "available_balance": Decimal("0.00"),
                    "currency": bill.currency,
                    "status": WalletStatus.ACTIVE,
                    "created_by": user_id,
                    "last_modified_by": user_id,
                },
            )

            # Create pending transaction for direct payment
            transaction = Transaction.objects.create(
                cluster=cluster,
                wallet=wallet,
                type=TransactionType.BILL_PAYMENT,
                amount=amount,
                currency=wallet.currency,
                description=f"Direct bill payment - {bill.title}",
                status=TransactionStatus.PENDING,
                provider=provider,
                created_by=user_id,
                last_modified_by=user_id,
                metadata={
                    "bill_id": str(bill.id),
                    "bill_number": bill.bill_number,
                    "bill_type": bill.type,
                    "payment_method": "direct",
                }
            )

            # Initialize payment with provider
            payment_response = payments.initialize(
                transaction=transaction,
                user_email=request.user.email_address,
                callback_url=callback_url,
            )

            response_serializer = DepositResponseSerializer(
                {
                    "transaction_id": transaction.transaction_id,
                    "amount": amount,
                    "currency": transaction.currency,
                    "provider": transaction.provider,
                    "payment_url": payment_response.get("authorization_url")
                    or payment_response.get("link"),
                    "reference": payment_response.get("reference")
                    or payment_response.get("tx_ref"),
                }
            )

            return success_response(
                data=response_serializer.data,
                message="Direct bill payment initialized successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error initializing direct bill payment: {e}")
            return error_response(
                message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@audit_viewset(resource_type="recurring_payment")
class RecurringPaymentViewSet(viewsets.ViewSet):
    """
    ViewSet for recurring payment operations (residents).
    """

    permission_classes = [
        IsAuthenticated,
        HasSpecificPermission([PaymentsPermissions.ViewWallet]),
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringPaymentFilter

    @action(
        detail=False, methods=["get"], url_path="my-payments", url_name="my-payments"
    )
    def my_payments(self, request):
        """
        Get user's recurring payments with filtering and pagination.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            queryset = RecurringPayment.objects.filter(
                cluster=cluster, user_id=user_id
            ).order_by("-created_at")

            filterset = RecurringPaymentFilter(
                request.GET, queryset=queryset, request=request
            )
            if filterset.is_valid():
                queryset = filterset.qs

            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request)

            payment_serializer = RecurringPaymentSerializer(page, many=True)

            pagination_data = {
                "page": paginator.page.number,
                "page_size": paginator.page_size,
                "total_count": paginator.page.paginator.count,
                "total_pages": paginator.page.paginator.num_pages,
            }

            response_serializer = RecurringPaymentListResponseSerializer(
                {
                    "recurring_payments": payment_serializer.data,
                    "pagination": pagination_data,
                }
            )

            return success_response(
                data=response_serializer.data,
                message="Recurring payments retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving recurring payments: {e}")
            return error_response(
                message="Failed to retrieve recurring payments",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="summary", url_name="summary")
    def summary(self, request):
        """
        Get user's recurring payments summary.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            summary = recurring_payments.get_summary(
                cluster, user_id
            )

            return success_response(
                data=summary,
                message="Recurring payments summary retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving recurring payments summary: {e}")
            return error_response(
                message="Failed to retrieve recurring payments summary",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        """
        Create a new recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = CreateRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data

            try:
                wallet = Wallet.objects.get(cluster=cluster, user_id=user_id)
            except Wallet.DoesNotExist:
                return error_response(
                    message="Wallet not found", status_code=status.HTTP_404_NOT_FOUND
                )

            bill = None
            if validated_data.get("bill_id"):
                try:
                    bill = Bill.objects.get(
                        id=validated_data["bill_id"], cluster=cluster, user_id=user_id
                    )
                except Bill.DoesNotExist:
                    return error_response(
                        message="Bill not found", status_code=status.HTTP_404_NOT_FOUND
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
                created_by=user_id,
                bill=bill,
                utility_provider=utility_provider,
                customer_id=validated_data.get("customer_id"),
                payment_source=validated_data.get("payment_source", "wallet"),
                spending_limit=validated_data.get("spending_limit"),
            )

            payment_serializer = RecurringPaymentSerializer(payment)

            return success_response(
                data=payment_serializer.data,
                message="Recurring payment created successfully",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating recurring payment: {e}")
            return error_response(
                message="Failed to create recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="pause-payment",
        url_name="pause_payment",
    )
    def pause(self, request):
        """
        Pause a recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            payment_id = serializer.validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster, user_id=user_id
            )

            success = recurring_payments.pause(
                payment=payment, paused_by=user_id
            )

            if success:
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
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

    @action(
        detail=False,
        methods=["post"],
        url_path="resume-payment",
        url_name="resume_payment",
    )
    def resume(self, request):
        """
        Resume a paused recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            payment_id = serializer.validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster, user_id=user_id
            )

            success = recurring_payments.resume(
                payment=payment, resumed_by=user_id
            )

            if success:
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
                    message="Recurring payment resumed successfully",
                )
            else:
                return error_response(
                    message="Cannot resume recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error resuming recurring payment: {e}")
            return error_response(
                message="Failed to resume recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="cancel-payment",
        url_name="cancel_payment",
    )
    def cancel(self, request):
        """
        Cancel a recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = PauseRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            payment_id = serializer.validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster, user_id=user_id
            )

            success = recurring_payments.cancel(
                payment=payment, cancelled_by=user_id
            )

            if success:
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
                    message="Recurring payment cancelled successfully",
                )
            else:
                return error_response(
                    message="Recurring payment is already cancelled",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error cancelling recurring payment: {e}")
            return error_response(
                message="Failed to cancel recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request):
        """
        Update a recurring payment.
        """
        try:
            cluster = request.cluster_context
            user_id = str(request.user.id)

            serializer = UpdateRecurringPaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    message="Invalid input data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            payment_id = validated_data["payment_id"]

            payment = get_object_or_404(
                RecurringPayment, id=payment_id, cluster=cluster, user_id=user_id
            )

            bill = None
            if "bill_id" in validated_data and validated_data["bill_id"]:
                bill = get_object_or_404(
                    Bill, id=validated_data["bill_id"], cluster=cluster, user_id=user_id
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
                updated_by=user_id,
            )

            if success:
                payment_serializer = RecurringPaymentSerializer(payment)
                return success_response(
                    data=payment_serializer.data,
                    message="Recurring payment updated successfully",
                )
            else:
                return error_response(
                    message="Cannot update recurring payment in current status",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error updating recurring payment: {e}")
            return error_response(
                message="Failed to update recurring payment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
