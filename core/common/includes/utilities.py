"""
Utility service functions for bill payments.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any
from django.utils import timezone
from django.db import transaction

from core.common.models import (
    Transaction,
    TransactionType,
    TransactionStatus,
    PaymentProvider,
    PaymentError,
    UtilityProvider,
    Bill,
    BillCategory,
    BillStatus,
)
from core.common.models.payments.payment_error import (
    PaymentErrorType,
    PaymentErrorSeverity,
)

logger = logging.getLogger("clustr")


# Paystack utility functions
def validate_paystack_customer(customer_id: str, provider_code: str) -> Dict[str, Any]:
    """
    Validate customer with Paystack Bills API.

    Args:
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing validation result and customer info
    """
    try:
        # TODO: Implement actual Paystack API call
        # For now, return mock response
        return {
            "success": True,
            "customer_name": "Mock Customer",
            "customer_id": customer_id,
            "address": "Mock Address",
            "provider_code": provider_code,
        }
    except Exception as e:
        logger.error(f"Paystack customer validation failed: {str(e)}")
        return {"success": False, "error": str(e)}


def get_paystack_customer_info(customer_id: str, provider_code: str) -> Dict[str, Any]:
    """
    Get customer info from Paystack Bills API.

    Args:
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing customer information
    """
    try:
        # TODO: Implement actual Paystack API call
        return {
            "success": True,
            "customer_name": "Mock Customer",
            "customer_id": customer_id,
            "outstanding_balance": "0.00",
            "provider_code": provider_code,
        }
    except Exception as e:
        logger.error(f"Paystack customer info lookup failed: {str(e)}")
        return {"success": False, "error": str(e)}


def purchase_paystack_utility(
    customer_id: str, amount: Decimal, provider_code: str, **kwargs
) -> Dict[str, Any]:
    """
    Purchase utility via Paystack Bills API.

    Args:
        customer_id: Customer ID or meter number
        amount: Payment amount
        provider_code: Utility provider code
        **kwargs: Additional parameters (e.g., meter_type, bundle_code)

    Returns:
        Dict containing transaction result
    """
    try:
        # TODO: Implement actual Paystack API call
        # Mock response now includes a token for electricity purchases
        reference = kwargs.get("reference", "")
        response_data = {
            "success": True,
            "transaction_id": f"PSK_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            "reference": reference,
            "amount": str(amount),
            "customer_id": customer_id,
            "provider_code": provider_code,
            "status": "success",
            "metadata": kwargs,  # Store sent params
        }

        # Example of handling different utility types based on provider code or kwargs
        if "electric" in provider_code or kwargs.get("service_type") == "electricity":
            response_data["token"] = "0123-4567-8901-2345-6789"
            response_data["units"] = f"{amount / Decimal('50.0')}"  # Mock calculation

        if "data" in provider_code or kwargs.get("service_type") == "internet":
            response_data["bundle"] = kwargs.get("bundle_code", "Default Bundle")

        return response_data
    except Exception as e:
        logger.error(f"Paystack utility purchase failed: {str(e)}")
        return {"success": False, "error": str(e)}


def get_paystack_utility_providers(service_type: str) -> List[Dict[str, Any]]:
    """
    Get Paystack utility providers.

    Args:
        service_type: Type of utility service

    Returns:
        List of available providers
    """
    # TODO: Implement actual API call to get providers
    mock_providers = {
        "electricity": [
            {"name": "Ikeja Electric", "code": "ikeja-electric"},
            {"name": "Eko Electric", "code": "eko-electric"},
        ],
        "water": [
            {"name": "Lagos Water Corporation", "code": "lagos-water"},
        ],
        "internet": [
            {"name": "MTN Data", "code": "mtn-data"},
            {"name": "Airtel Data", "code": "airtel-data"},
        ],
    }
    return mock_providers.get(service_type, [])


# Flutterwave utility functions
def validate_flutterwave_customer(
    customer_id: str, provider_code: str
) -> Dict[str, Any]:
    """
    Validate customer with Flutterwave Bills API.

    Args:
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing validation result and customer info
    """
    try:
        # TODO: Implement actual Flutterwave API call
        return {
            "success": True,
            "customer_name": "Mock Customer",
            "customer_id": customer_id,
            "address": "Mock Address",
            "provider_code": provider_code,
        }
    except Exception as e:
        logger.error(f"Flutterwave customer validation failed: {str(e)}")
        return {"success": False, "error": str(e)}


def get_flutterwave_customer_info(
    customer_id: str, provider_code: str
) -> Dict[str, Any]:
    """
    Get customer info from Flutterwave Bills API.

    Args:
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing customer information
    """
    try:
        # TODO: Implement actual Flutterwave API call
        return {
            "success": True,
            "customer_name": "Mock Customer",
            "customer_id": customer_id,
            "outstanding_balance": "0.00",
            "provider_code": provider_code,
        }
    except Exception as e:
        logger.error(f"Flutterwave customer info lookup failed: {str(e)}")
        return {"success": False, "error": str(e)}


def purchase_flutterwave_utility(
    customer_id: str, amount: Decimal, provider_code: str, **kwargs
) -> Dict[str, Any]:
    """
    Purchase utility via Flutterwave Bills API.

    Args:
        customer_id: Customer ID or meter number
        amount: Payment amount
        provider_code: Utility provider code
        **kwargs: Additional parameters (e.g., meter_type, bundle_code)

    Returns:
        Dict containing transaction result
    """
    try:
        # TODO: Implement actual Flutterwave API call
        reference = kwargs.get("reference", "")
        response_data = {
            "success": True,
            "transaction_id": f"FLW_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            "reference": reference,
            "amount": str(amount),
            "customer_id": customer_id,
            "provider_code": provider_code,
            "status": "success",
            "metadata": kwargs,
        }

        if "electric" in provider_code or kwargs.get("service_type") == "electricity":
            response_data["token"] = "9876-5432-1098-7654-3210"
            response_data["units"] = f"{amount / Decimal('52.5')}"

        if "data" in provider_code or kwargs.get("service_type") == "internet":
            response_data["bundle"] = kwargs.get("bundle_code", "Default Data Plan")

        return response_data
    except Exception as e:
        logger.error(f"Flutterwave utility purchase failed: {str(e)}")
        return {"success": False, "error": str(e)}


def get_flutterwave_utility_providers(service_type: str) -> List[Dict[str, Any]]:
    """
    Get Flutterwave utility providers.

    Args:
        service_type: Type of utility service

    Returns:
        List of available providers
    """
    # TODO: Implement actual API call to get providers
    mock_providers = {
        "electricity": [
            {"name": "Ikeja Electric", "code": "ikeja-electric"},
            {"name": "Eko Electric", "code": "eko-electric"},
        ],
        "water": [
            {"name": "Lagos Water Corporation", "code": "lagos-water"},
        ],
        "internet": [
            {"name": "MTN Data", "code": "mtn-data"},
            {"name": "Airtel Data", "code": "airtel-data"},
        ],
    }
    return mock_providers.get(service_type, [])


# Provider selection functions
def validate_customer(
    provider: str, customer_id: str, provider_code: str
) -> Dict[str, Any]:
    """
    Validate customer ID with utility provider.

    Args:
        provider: Payment provider (paystack/flutterwave)
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing validation result and customer info
    """
    if provider == PaymentProvider.PAYSTACK:
        return validate_paystack_customer(customer_id, provider_code)
    elif provider == PaymentProvider.FLUTTERWAVE:
        return validate_flutterwave_customer(customer_id, provider_code)
    else:
        raise ValueError(f"Unsupported utility provider: {provider}")


def get_customer_info(
    provider: str, customer_id: str, provider_code: str
) -> Dict[str, Any]:
    """
    Get customer information from utility provider.

    Args:
        provider: Payment provider (paystack/flutterwave)
        customer_id: Customer ID or meter number
        provider_code: Utility provider code

    Returns:
        Dict containing customer information
    """
    if provider == PaymentProvider.PAYSTACK:
        return get_paystack_customer_info(customer_id, provider_code)
    elif provider == PaymentProvider.FLUTTERWAVE:
        return get_flutterwave_customer_info(customer_id, provider_code)
    else:
        raise ValueError(f"Unsupported utility provider: {provider}")


def purchase_utility(
    provider: str, customer_id: str, amount: Decimal, provider_code: str, **kwargs
) -> Dict[str, Any]:
    """
    Purchase utility service for customer.

    Args:
        provider: Payment provider (paystack/flutterwave)
        customer_id: Customer ID or meter number
        amount: Payment amount
        provider_code: Utility provider code
        **kwargs: Additional parameters (e.g., meter_type, bundle_code)

    Returns:
        Dict containing transaction result
    """
    if provider == PaymentProvider.PAYSTACK:
        return purchase_paystack_utility(customer_id, amount, provider_code, **kwargs)
    elif provider == PaymentProvider.FLUTTERWAVE:
        return purchase_flutterwave_utility(
            customer_id, amount, provider_code, **kwargs
        )
    else:
        raise ValueError(f"Unsupported utility provider: {provider}")


def get_utility_providers(provider: str, service_type: str) -> List[Dict[str, Any]]:
    """
    Get available utility providers for a service type.

    Args:
        provider: Payment provider (paystack/flutterwave)
        service_type: Type of utility service

    Returns:
        List of available providers
    """
    if provider == PaymentProvider.PAYSTACK:
        return get_paystack_utility_providers(service_type)
    elif provider == PaymentProvider.FLUTTERWAVE:
        return get_flutterwave_utility_providers(service_type)
    else:
        raise ValueError(f"Unsupported utility provider: {provider}")


# Payment processing functions
def setup_recurring_utility_payment(
    user_id: str,
    utility_provider: UtilityProvider,
    customer_id: str,
    amount: Decimal,
    frequency: str,
    wallet,
    **kwargs,
) -> Dict[str, Any]:
    """
    Set up recurring utility payment.

    Args:
        user_id: User ID
        utility_provider: UtilityProvider instance
        customer_id: Customer ID or meter number
        amount: Payment amount
        frequency: Payment frequency
        wallet: User wallet
        **kwargs: Additional parameters for the recurring payment and utility purchase.
                  (e.g., title, description, start_date, meter_type, bundle_code)

    Returns:
        Dict containing setup result
    """
    try:
        # Validate customer first
        validation_result = validate_customer(
            utility_provider.api_provider, customer_id, utility_provider.provider_code
        )

        if not validation_result.get("success"):
            return {
                "success": False,
                "error": "Customer validation failed",
                "details": validation_result.get("error"),
            }

        # Check amount limits
        if not utility_provider.is_amount_valid(amount):
            return {
                "success": False,
                "error": f"Amount must be between {utility_provider.minimum_amount} and {utility_provider.maximum_amount}",
            }

        # Separate kwargs for model fields from metadata
        model_kwargs = {
            "title": kwargs.pop("title", f"{utility_provider.name} - {customer_id}"),
            "description": kwargs.pop(
                "description", f"Automated {utility_provider.name} payment"
            ),
            "payment_source": kwargs.pop("payment_source", "wallet"),
            "spending_limit": kwargs.pop("spending_limit", None),
            "start_date": kwargs.pop("start_date", timezone.now()),
        }
        model_kwargs["next_payment_date"] = kwargs.pop(
            "next_payment_date", model_kwargs["start_date"]
        )

        # The rest of kwargs are considered metadata for the utility payment
        payment_metadata = kwargs

        # Create recurring payment
        from core.common.models import RecurringPayment, RecurringPaymentStatus

        recurring_payment = RecurringPayment.objects.create(
            cluster=utility_provider.cluster,
            user_id=user_id,
            wallet=wallet,
            amount=amount,
            frequency=frequency,
            utility_provider=utility_provider,
            customer_id=customer_id,
            status=RecurringPaymentStatus.ACTIVE,
            created_by=user_id,
            last_modified_by=user_id,
            metadata=payment_metadata,
            **model_kwargs,
        )

        return {
            "success": True,
            "recurring_payment_id": recurring_payment.id,
            "message": "Recurring utility payment set up successfully",
        }

    except Exception as e:
        logger.error(f"Failed to setup recurring utility payment: {str(e)}")
        return {
            "success": False,
            "error": "Failed to setup recurring payment",
            "details": str(e),
        }


@transaction.atomic
def process_utility_payment(
    user_id: str,
    utility_provider: UtilityProvider,
    customer_id: str,
    amount: Decimal,
    wallet,
    description: str = None,
    idempotency_key: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Process one-time utility payment.

    Args:
        user_id: User ID
        utility_provider: UtilityProvider instance
        customer_id: Customer ID or meter number
        amount: Payment amount
        wallet: User wallet
        description: Payment description
        **kwargs: Additional parameters for the utility purchase (e.g., meter_type, bundle_code)

    Returns:
        Dict containing payment result
    """
    try:
        # Check wallet balance
        if not wallet.has_sufficient_balance(amount):
            return {"success": False, "error": "Insufficient wallet balance"}

        # Check amount limits
        if not utility_provider.is_amount_valid(amount):
            return {
                "success": False,
                "error": f"Amount must be between {utility_provider.minimum_amount} and {utility_provider.maximum_amount}",
            }

        # Check for duplicate payment using idempotency key
        if idempotency_key:
            existing_transaction = Transaction.objects.filter(
                idempotency_key=idempotency_key,
                wallet=wallet
            ).first()
            if existing_transaction:
                logger.info(f"Duplicate utility payment attempt detected with idempotency key: {idempotency_key}")
                # Return existing transaction result
                existing_bill = Bill.objects.filter(payment_transaction=existing_transaction).first()
                return {
                    "success": True,
                    "transaction_id": existing_transaction.transaction_id,
                    "bill_id": existing_bill.id if existing_bill else None,
                    "message": "Payment already processed (duplicate request)",
                }

        # Freeze amount in wallet
        if not wallet.freeze_amount(amount):
            return {"success": False, "error": "Failed to freeze amount in wallet"}

        # Prepare metadata for the transaction, including additional parameters
        transaction_metadata = {
            "utility_provider_id": utility_provider.id,
            "customer_id": customer_id,
            "provider_code": utility_provider.provider_code,
            **kwargs,
        }

        # Create pending transaction
        transaction = Transaction.objects.create(
            cluster=utility_provider.cluster,
            wallet=wallet,
            type=TransactionType.BILL_PAYMENT,
            amount=amount,
            currency=wallet.currency,
            description=description or f"Utility payment to {utility_provider.name}",
            status=TransactionStatus.PENDING,
            provider=utility_provider.api_provider,
            metadata=transaction_metadata,
            idempotency_key=idempotency_key,
            created_by=user_id,
            last_modified_by=user_id,
        )

        try:
            # Process payment via utility service
            result = purchase_utility(
                provider=utility_provider.api_provider,
                customer_id=customer_id,
                amount=amount,
                provider_code=utility_provider.provider_code,
                reference=transaction.transaction_id,
                **kwargs,  # Pass additional params to provider
            )

            if result.get("success"):
                # Mark transaction as completed
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = timezone.now()
                transaction.provider_response = result
                transaction.save()

                # Update wallet balance
                wallet.update_balance(amount, TransactionType.BILL_PAYMENT)

                # Create utility bill record
                bill = Bill.objects.create(
                    cluster=utility_provider.cluster,
                    user_id=user_id,
                    title=f"{utility_provider.name} Payment",
                    description=f"Utility payment for customer {customer_id}",
                    type=utility_provider.provider_type,
                    category=BillCategory.USER_MANAGED,
                    created_by_user=True,
                    amount=amount,
                    currency=wallet.currency,
                    status=BillStatus.PAID,
                    utility_provider=utility_provider,
                    customer_id=customer_id,
                    due_date=timezone.now(),
                    paid_at=timezone.now(),
                    payment_transaction=transaction,
                    created_by=user_id,
                    last_modified_by=user_id,
                )

                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "bill_id": bill.id,
                    "provider_transaction_id": result.get("transaction_id"),
                    "token": result.get("token"),  # Return token if available
                    "message": "Utility payment processed successfully",
                }
            else:
                # Mark transaction as failed and unfreeze amount
                transaction.mark_as_failed(result.get("error", "Payment failed"))

                # Create payment error record
                PaymentError.objects.create(
                    cluster=utility_provider.cluster,
                    transaction=transaction,
                    error_type=PaymentErrorType.UTILITY_PROVIDER_ERROR,
                    severity=PaymentErrorSeverity.HIGH,
                    provider_error_message=result.get("error", "Unknown error"),
                    user_friendly_message="Utility payment failed. Please try again.",
                    created_by=user_id,
                    last_modified_by=user_id,
                )

                return {
                    "success": False,
                    "error": "Utility payment failed",
                    "details": result.get("error"),
                }

        except Exception as e:
            # Mark transaction as failed and unfreeze amount
            transaction.mark_as_failed(str(e))

            logger.error(f"Utility payment processing failed: {str(e)}")
            return {
                "success": False,
                "error": "Payment processing failed",
                "details": str(e),
            }

    except Exception as e:
        logger.error(f"Utility payment setup failed: {str(e)}")
        return {"success": False, "error": "Payment setup failed", "details": str(e)}


def validate_utility_customer(
    utility_provider: UtilityProvider, customer_id: str
) -> Dict[str, Any]:
    """
    Validate utility customer.

    Args:
        utility_provider: UtilityProvider instance
        customer_id: Customer ID or meter number

    Returns:
        Dict containing validation result
    """
    try:
        return validate_customer(
            utility_provider.api_provider, customer_id, utility_provider.provider_code
        )
    except Exception as e:
        logger.error(f"Customer validation failed: {str(e)}")
        return {"success": False, "error": str(e)}


def get_user_utility_bills(
    user_id: str, cluster, bill_type: str = None, status: str = None
) -> List[Bill]:
    """
    Get user's utility bills.

    Args:
        user_id: User ID
        cluster: User's cluster
        bill_type: Filter by bill type (optional)
        status: Filter by status (optional)

    Returns:
        List of Bill objects
    """
    queryset = Bill.objects.filter(
        user_id=user_id, cluster=cluster, category=BillCategory.USER_MANAGED
    )

    if bill_type:
        queryset = queryset.filter(type=bill_type)

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


