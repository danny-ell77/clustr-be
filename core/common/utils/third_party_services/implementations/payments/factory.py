import logging
from core.common.models.wallet import (
    PaymentProvider,
)
from core.common.utils.third_party_services.implementations.payments.paystack import PaystackProvider
from core.common.utils.third_party_services.implementations.payments.flutterwave import FlutterwaveProvider

logger = logging.getLogger("clustr")

class PaymentProviderFactory:
    """Factory for creating payment provider instances."""
    
    _providers = {
        PaymentProvider.PAYSTACK: PaystackProvider,
        PaymentProvider.FLUTTERWAVE: FlutterwaveProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_type: PaymentProvider) -> PaymentProviderInterface:
        """Get a payment provider instance."""
        if provider_type not in cls._providers:
            raise PaymentProviderError(f"Unsupported payment provider: {provider_type}")
        
        try:
            return cls._providers[provider_type]()
        except Exception as e:
            logger.error(f"Failed to initialize payment provider {provider_type}: {e}")
            raise PaymentProviderError(f"Failed to initialize payment provider: {str(e)}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available payment providers."""
        available = []
        for provider_type in cls._providers:
            try:
                cls.get_provider(provider_type)
                available.append(provider_type)
            except PaymentProviderError:
                continue
        return available

