from typing import Any, Optional
import logging
from decimal import Decimal
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import requests
from core.common.utils.third_party_services.interfaces.payments import PaymentProviderInterface, PaymentProviderError

logger = logging.getLogger("clustr")

class FlutterwaveProvider(PaymentProviderInterface):
    """Flutterwave payment provider implementation."""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '')
        self.public_key = getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', '')
        self.base_url = "https://api.flutterwave.com/v3"
        
        if not self.secret_key:
            raise PaymentProviderError("Flutterwave secret key not configured")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict[str, Any]:
        """Make HTTP request to Flutterwave API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Flutterwave API request failed: {e}")
            raise PaymentProviderError(f"API request failed: {str(e)}")
    
    def initialize_payment(self, amount: Decimal, currency: str, email: str, 
                         callback_url: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        """Initialize a payment transaction with Flutterwave."""
        import uuid
        
        data = {
            'tx_ref': f"clustr-{uuid.uuid4().hex[:12]}",
            'amount': str(amount),
            'currency': currency,
            'redirect_url': callback_url,
            'customer': {
                'email': email,
            },
            'customizations': {
                'title': 'ClustR Payment',
                'description': 'Payment for ClustR services',
            },
        }
        
        if metadata:
            data['meta'] = metadata
        
        response = self._make_request('POST', '/payments', data)
        
        if response.get('status') == 'success':
            return {
                'success': True,
                'reference': data['tx_ref'],
                'authorization_url': response['data']['link'],
                'tx_ref': data['tx_ref'],
            }
        else:
            raise PaymentProviderError(f"Payment initialization failed: {response.get('message', 'Unknown error')}")
    
    def verify_payment(self, reference: str) -> dict[str, Any]:
        """Verify a payment transaction with Flutterwave."""
        response = self._make_request('GET', f'/transactions/{reference}/verify')
        
        if response.get('status') == 'success':
            data = response['data']
            return {
                'success': data['status'] == 'successful',
                'amount': Decimal(data['amount']),
                'currency': data['currency'],
                'reference': data['tx_ref'],
                'status': data['status'],
                'gateway_response': data.get('processor_response', ''),
                'paid_at': data.get('created_at'),
                'channel': data.get('payment_type'),
                'fees': Decimal(data.get('app_fee', 0)),
                'customer': data.get('customer', {}),
                'metadata': data.get('meta', {}),
            }
        else:
            raise PaymentProviderError(f"Payment verification failed: {response.get('message', 'Unknown error')}")
    
    def initiate_transfer(self, amount: Decimal, recipient_code: str, 
                         reason: str, currency: str = "NGN") -> dict[str, Any]:
        """Initiate a transfer with Flutterwave."""
        import uuid
        
        data = {
            'account_bank': recipient_code,  # Bank code for Flutterwave
            'account_number': recipient_code,  # This would need to be passed differently
            'amount': float(amount),
            'narration': reason,
            'currency': currency,
            'reference': f"clustr-transfer-{uuid.uuid4().hex[:12]}",
            'callback_url': getattr(settings, 'FLUTTERWAVE_TRANSFER_CALLBACK_URL', ''),
            'debit_currency': currency,
        }
        
        response = self._make_request('POST', '/transfers', data)
        
        if response.get('status') == 'success':
            data = response['data']
            return {
                'success': True,
                'transfer_id': data['id'],
                'reference': data['reference'],
                'status': data['status'],
                'amount': Decimal(data['amount']),
                'currency': data['currency'],
            }
        else:
            raise PaymentProviderError(f"Transfer initiation failed: {response.get('message', 'Unknown error')}")
    
    def create_transfer_recipient(self, account_number: str, bank_code: str, 
                                name: str, currency: str = "NGN") -> dict[str, Any]:
        """Create a transfer recipient with Flutterwave (not needed, direct transfer)."""
        # Flutterwave doesn't require recipient creation, return account details
        return {
            'success': True,
            'recipient_code': bank_code,  # Use bank code as recipient code
            'account_number': account_number,
            'bank_code': bank_code,
            'name': name,
        }
    
    def verify_account(self, account_number: str, bank_code: str) -> dict[str, Any]:
        """Verify a bank account with Flutterwave."""
        data = {
            'account_number': account_number,
            'account_bank': bank_code,
        }
        
        response = self._make_request('POST', '/accounts/resolve', data)
        
        if response.get('status') == 'success':
            data = response['data']
            return {
                'success': True,
                'account_number': data['account_number'],
                'account_name': data['account_name'],
                'bank_code': bank_code,
            }
        else:
            raise PaymentProviderError(f"Account verification failed: {response.get('message', 'Unknown error')}")
    
    def get_banks(self) -> dict[str, Any]:
        """Get list of supported banks from Flutterwave."""
        response = self._make_request('GET', '/banks/NG')  # Nigeria banks
        
        if response.get('status') == 'success':
            return {
                'success': True,
                'banks': response['data'],
            }
        else:
            raise PaymentProviderError(f"Failed to get banks: {response.get('message', 'Unknown error')}")

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify Flutterwave webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            
        Returns:
            bool: True if signature is valid
        """
        expected_signature = hashlib.sha256(
            (getattr(settings, 'FLUTTERWAVE_WEBHOOK_SECRET', '') + payload).encode('utf-8')
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    
