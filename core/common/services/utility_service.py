"""
Utility service interfaces and implementations for bill payments.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Any, Optional
from django.utils import timezone

from core.common.models import (
    Transaction, 
    TransactionType, 
    TransactionStatus,
    PaymentProvider,
    PaymentError,
    UtilityProvider,
    Bill,
    BillCategory,
    BillStatus
)
from core.common.models.payments.payment_error import PaymentErrorType, PaymentErrorSeverity

logger = logging.getLogger("clustr")


class UtilityServiceInterface(ABC):
    """Abstract interface for utility service providers."""

    @abstractmethod
    def validate_customer(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """
        Validate customer ID with utility provider.
        
        Args:
            customer_id: Customer ID or meter number
            provider_code: Utility provider code
            
        Returns:
            Dict containing validation result and customer info
        """
        pass

    @abstractmethod
    def get_customer_info(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """
        Get customer information from utility provider.
        
        Args:
            customer_id: Customer ID or meter number
            provider_code: Utility provider code
            
        Returns:
            Dict containing customer information
        """
        pass

    @abstractmethod
    def purchase_utility(self, customer_id: str, amount: Decimal, provider_code: str, **kwargs) -> Dict[str, Any]:
        """
        Purchase utility service for customer.
        
        Args:
            customer_id: Customer ID or meter number
            amount: Payment amount
            provider_code: Utility provider code
            **kwargs: Additional parameters
            
        Returns:
            Dict containing transaction result
        """
        pass

    @abstractmethod
    def get_utility_providers(self, service_type: str) -> List[Dict[str, Any]]:
        """
        Get available utility providers for a service type.
        
        Args:
            service_type: Type of utility service
            
        Returns:
            List of available providers
        """
        pass


class PaystackUtilityService(UtilityServiceInterface):
    """Paystack implementation of utility service interface."""

    def __init__(self):
        self.base_url = "https://api.paystack.co"
        # TODO: Get API key from settings
        self.api_key = None

    def validate_customer(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """Validate customer with Paystack Bills API."""
        try:
            # TODO: Implement actual Paystack API call
            # For now, return mock response
            return {
                "success": True,
                "customer_name": "Mock Customer",
                "customer_id": customer_id,
                "address": "Mock Address",
                "provider_code": provider_code
            }
        except Exception as e:
            logger.error(f"Paystack customer validation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_customer_info(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """Get customer info from Paystack Bills API."""
        try:
            # TODO: Implement actual Paystack API call
            return {
                "success": True,
                "customer_name": "Mock Customer",
                "customer_id": customer_id,
                "outstanding_balance": "0.00",
                "provider_code": provider_code
            }
        except Exception as e:
            logger.error(f"Paystack customer info lookup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def purchase_utility(self, customer_id: str, amount: Decimal, provider_code: str, **kwargs) -> Dict[str, Any]:
        """Purchase utility via Paystack Bills API."""
        try:
            # TODO: Implement actual Paystack API call
            return {
                "success": True,
                "transaction_id": f"PSK_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                "reference": kwargs.get("reference", ""),
                "amount": str(amount),
                "customer_id": customer_id,
                "provider_code": provider_code,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Paystack utility purchase failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_utility_providers(self, service_type: str) -> List[Dict[str, Any]]:
        """Get Paystack utility providers."""
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
            ]
        }
        return mock_providers.get(service_type, [])


class FlutterwaveUtilityService(UtilityServiceInterface):
    """Flutterwave implementation of utility service interface."""

    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        # TODO: Get API key from settings
        self.api_key = None

    def validate_customer(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """Validate customer with Flutterwave Bills API."""
        try:
            # TODO: Implement actual Flutterwave API call
            return {
                "success": True,
                "customer_name": "Mock Customer",
                "customer_id": customer_id,
                "address": "Mock Address",
                "provider_code": provider_code
            }
        except Exception as e:
            logger.error(f"Flutterwave customer validation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_customer_info(self, customer_id: str, provider_code: str) -> Dict[str, Any]:
        """Get customer info from Flutterwave Bills API."""
        try:
            # TODO: Implement actual Flutterwave API call
            return {
                "success": True,
                "customer_name": "Mock Customer",
                "customer_id": customer_id,
                "outstanding_balance": "0.00",
                "provider_code": provider_code
            }
        except Exception as e:
            logger.error(f"Flutterwave customer info lookup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def purchase_utility(self, customer_id: str, amount: Decimal, provider_code: str, **kwargs) -> Dict[str, Any]:
        """Purchase utility via Flutterwave Bills API."""
        try:
            # TODO: Implement actual Flutterwave API call
            return {
                "success": True,
                "transaction_id": f"FLW_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                "reference": kwargs.get("reference", ""),
                "amount": str(amount),
                "customer_id": customer_id,
                "provider_code": provider_code,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Flutterwave utility purchase failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_utility_providers(self, service_type: str) -> List[Dict[str, Any]]:
        """Get Flutterwave utility providers."""
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
            ]
        }
        return mock_providers.get(service_type, [])


class UtilityServiceFactory:
    """Factory for creating utility service instances."""

    @staticmethod
    def get_service(provider: str) -> UtilityServiceInterface:
        """
        Get utility service instance based on provider.
        
        Args:
            provider: Payment provider (paystack/flutterwave)
            
        Returns:
            UtilityServiceInterface instance
        """
        if provider == PaymentProvider.PAYSTACK:
            return PaystackUtilityService()
        elif provider == PaymentProvider.FLUTTERWAVE:
            return FlutterwaveUtilityService()
        else:
            raise ValueError(f"Unsupported utility provider: {provider}")


class UtilityPaymentManager:
    """Manager class for utility payment operations."""

    @staticmethod
    def setup_recurring_utility_payment(
        user_id: str,
        utility_provider: UtilityProvider,
        customer_id: str,
        amount: Decimal,
        frequency: str,
        wallet,
        **kwargs
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
            **kwargs: Additional parameters
            
        Returns:
            Dict containing setup result
        """
        try:
            # Validate customer first
            service = UtilityServiceFactory.get_service(utility_provider.api_provider)
            validation_result = service.validate_customer(customer_id, utility_provider.provider_code)
            
            if not validation_result.get("success"):
                return {
                    "success": False,
                    "error": "Customer validation failed",
                    "details": validation_result.get("error")
                }

            # Check amount limits
            if not utility_provider.is_amount_valid(amount):
                return {
                    "success": False,
                    "error": f"Amount must be between {utility_provider.minimum_amount} and {utility_provider.maximum_amount}"
                }

            # Create recurring payment
            from core.common.models import RecurringPayment, RecurringPaymentStatus
            
            recurring_payment = RecurringPayment.objects.create(
                cluster=utility_provider.cluster,
                user_id=user_id,
                wallet=wallet,
                title=kwargs.get("title", f"{utility_provider.name} - {customer_id}"),
                description=kwargs.get("description", f"Automated {utility_provider.name} payment"),
                amount=amount,
                frequency=frequency,
                utility_provider=utility_provider,
                customer_id=customer_id,
                payment_source=kwargs.get("payment_source", "wallet"),
                spending_limit=kwargs.get("spending_limit"),
                start_date=kwargs.get("start_date", timezone.now()),
                next_payment_date=kwargs.get("next_payment_date", timezone.now()),
                status=RecurringPaymentStatus.ACTIVE,
                created_by=user_id,
                last_modified_by=user_id,
            )

            return {
                "success": True,
                "recurring_payment_id": recurring_payment.id,
                "message": "Recurring utility payment set up successfully"
            }

        except Exception as e:
            logger.error(f"Failed to setup recurring utility payment: {str(e)}")
            return {
                "success": False,
                "error": "Failed to setup recurring payment",
                "details": str(e)
            }

    @staticmethod
    def process_utility_payment(
        user_id: str,
        utility_provider: UtilityProvider,
        customer_id: str,
        amount: Decimal,
        wallet,
        description: str = None
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
            
        Returns:
            Dict containing payment result
        """
        try:
            # Check wallet balance
            if not wallet.has_sufficient_balance(amount):
                return {
                    "success": False,
                    "error": "Insufficient wallet balance"
                }

            # Check amount limits
            if not utility_provider.is_amount_valid(amount):
                return {
                    "success": False,
                    "error": f"Amount must be between {utility_provider.minimum_amount} and {utility_provider.maximum_amount}"
                }

            # Freeze amount in wallet
            if not wallet.freeze_amount(amount):
                return {
                    "success": False,
                    "error": "Failed to freeze amount in wallet"
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
                metadata={
                    "utility_provider_id": utility_provider.id,
                    "customer_id": customer_id,
                    "provider_code": utility_provider.provider_code,
                },
                created_by=user_id,
                last_modified_by=user_id,
            )

            try:
                # Process payment via utility service
                service = UtilityServiceFactory.get_service(utility_provider.api_provider)
                result = service.purchase_utility(
                    customer_id=customer_id,
                    amount=amount,
                    provider_code=utility_provider.provider_code,
                    reference=transaction.transaction_id
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
                        amount=amount,
                        currency=wallet.currency,
                        status=BillStatus.PAID,
                        utility_provider=utility_provider,
                        customer_id=customer_id,
                        due_date=timezone.now(),
                        paid_amount=amount,
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
                        "message": "Utility payment processed successfully"
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
                        "details": result.get("error")
                    }

            except Exception as e:
                # Mark transaction as failed and unfreeze amount
                transaction.mark_as_failed(str(e))
                
                logger.error(f"Utility payment processing failed: {str(e)}")
                return {
                    "success": False,
                    "error": "Payment processing failed",
                    "details": str(e)
                }

        except Exception as e:
            logger.error(f"Utility payment setup failed: {str(e)}")
            return {
                "success": False,
                "error": "Payment setup failed",
                "details": str(e)
            }

    @staticmethod
    def validate_utility_customer(utility_provider: UtilityProvider, customer_id: str) -> Dict[str, Any]:
        """
        Validate utility customer.
        
        Args:
            utility_provider: UtilityProvider instance
            customer_id: Customer ID or meter number
            
        Returns:
            Dict containing validation result
        """
        try:
            service = UtilityServiceFactory.get_service(utility_provider.api_provider)
            return service.validate_customer(customer_id, utility_provider.provider_code)
        except Exception as e:
            logger.error(f"Customer validation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_user_utility_bills(user_id: str, cluster, bill_type: str = None, status: str = None) -> List[Bill]:
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
            user_id=user_id,
            cluster=cluster,
            category=BillCategory.USER_MANAGED
        )

        if bill_type:
            queryset = queryset.filter(type=bill_type)
        
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")