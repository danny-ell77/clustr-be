from decimal import Decimal
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""
    pass


class PaymentProviderInterface(ABC):
    """Abstract interface for payment providers."""
    
    @abstractmethod
    def initialize_payment(self, amount: Decimal, currency: str, email: str, 
                         callback_url: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        """Initialize a payment transaction."""
        pass
    
    @abstractmethod
    def verify_payment(self, reference: str) -> dict[str, Any]:
        """Verify a payment transaction."""
        pass
    
    @abstractmethod
    def initiate_transfer(self, amount: Decimal, recipient_code: str, 
                         reason: str, currency: str = "NGN") -> dict[str, Any]:
        """Initiate a transfer to a recipient."""
        pass
    
    @abstractmethod
    def create_transfer_recipient(self, account_number: str, bank_code: str, 
                                name: str, currency: str = "NGN") -> dict[str, Any]:
        """Create a transfer recipient."""
        pass
    
    @abstractmethod
    def verify_account(self, account_number: str, bank_code: str) -> dict[str, Any]:
        """Verify a bank account."""
        pass
    
    @abstractmethod
    def get_banks(self) -> dict[str, Any]:
        """Get list of supported banks."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: str, signature: str)-> bool:
        """Verify webhook signature."""
        pass

