from typing import Dict, Any
from decimal import Decimal
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import requests
from core.common.utils.third_party_services.interfaces.payments import PaymentProviderInterface, PaymentProviderError

class PaystackProvider(PaymentProviderInterface):
    """Paystack payment provider implementation."""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = "https://api.paystack.co"
        
        if not self.secret_key:
            raise PaymentProviderError("Paystack secret key not configured")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Paystack API."""
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
            logger.error(f"Paystack API request failed: {e}")
            raise PaymentProviderError(f"API request failed: {str(e)}")
    
    def initialize_payment(self, amount: Decimal, currency: str, email: str, 
                         callback_url: str, metadata: Dict = None) -> Dict[str, Any]:
        """Initialize a payment transaction with Paystack."""
        data = {
            'amount': int(amount * 100),  # Convert to kobo
            'currency': currency,
            'email': email,
            'callback_url': callback_url,
        }
        
        if metadata:
            data['metadata'] = metadata
        
        response = self._make_request('POST', '/transaction/initialize', data)
        
        if response.get('status'):
            return {
                'success': True,
                'reference': response['data']['reference'],
                'authorization_url': response['data']['authorization_url'],
                'access_code': response['data']['access_code'],
            }
        else:
            raise PaymentProviderError(f"Payment initialization failed: {response.get('message', 'Unknown error')}")
    
    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify a payment transaction with Paystack."""
        response = self._make_request('GET', f'/transaction/verify/{reference}')
        
        if response.get('status'):
            data = response['data']
            return {
                'success': data['status'] == 'success',
                'amount': Decimal(data['amount']) / 100,  # Convert from kobo
                'currency': data['currency'],
                'reference': data['reference'],
                'status': data['status'],
                'gateway_response': data.get('gateway_response', ''),
                'paid_at': data.get('paid_at'),
                'channel': data.get('channel'),
                'fees': Decimal(data.get('fees', 0)) / 100,
                'customer': data.get('customer', {}),
                'metadata': data.get('metadata', {}),
            }
        else:
            raise PaymentProviderError(f"Payment verification failed: {response.get('message', 'Unknown error')}")
    
    def initiate_transfer(self, amount: Decimal, recipient_code: str, 
                         reason: str, currency: str = "NGN") -> Dict[str, Any]:
        """Initiate a transfer with Paystack."""
        data = {
            'source': 'balance',
            'amount': int(amount * 100),  # Convert to kobo
            'recipient': recipient_code,
            'reason': reason,
            'currency': currency,
        }
        
        response = self._make_request('POST', '/transfer', data)
        
        if response.get('status'):
            data = response['data']
            return {
                'success': True,
                'transfer_code': data['transfer_code'],
                'reference': data['reference'],
                'status': data['status'],
                'amount': Decimal(data['amount']) / 100,
                'currency': data['currency'],
                'recipient': data['recipient'],
            }
        else:
            raise PaymentProviderError(f"Transfer initiation failed: {response.get('message', 'Unknown error')}")
    
    def create_transfer_recipient(self, account_number: str, bank_code: str, 
                                name: str, currency: str = "NGN") -> Dict[str, Any]:
        """Create a transfer recipient with Paystack."""
        data = {
            'type': 'nuban',
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': currency,
        }
        
        response = self._make_request('POST', '/transferrecipient', data)
        
        if response.get('status'):
            data = response['data']
            return {
                'success': True,
                'recipient_code': data['recipient_code'],
                'type': data['type'],
                'name': data['name'],
                'account_number': data['details']['account_number'],
                'bank_name': data['details']['bank_name'],
                'bank_code': data['details']['bank_code'],
            }
        else:
            raise PaymentProviderError(f"Recipient creation failed: {response.get('message', 'Unknown error')}")
    
    def verify_account(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        """Verify a bank account with Paystack."""
        params = {
            'account_number': account_number,
            'bank_code': bank_code,
        }
        
        response = self._make_request('GET', '/bank/resolve', params)
        
        if response.get('status'):
            data = response['data']
            return {
                'success': True,
                'account_number': data['account_number'],
                'account_name': data['account_name'],
                'bank_id': data['bank_id'],
            }
        else:
            raise PaymentProviderError(f"Account verification failed: {response.get('message', 'Unknown error')}")
    
    def get_banks(self) -> Dict[str, Any]:
        """Get list of supported banks from Paystack."""
        response = self._make_request('GET', '/bank')
        
        if response.get('status'):
            return {
                'success': True,
                'banks': response['data'],
            }
        else:
            raise PaymentProviderError(f"Failed to get banks: {response.get('message', 'Unknown error')}")

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify Paystack webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            
        Returns:
            bool: True if signature is valid
        """
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

