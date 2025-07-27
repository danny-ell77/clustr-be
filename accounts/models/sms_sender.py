"""
SMS sending functionality for ClustR application.
"""

import logging
from typing import Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.common.error_utils import log_exceptions
from core.common.exceptions import ExternalServiceException

logger = logging.getLogger('clustr')

class SMSSender:
    """
    Handles sending SMS messages for verification and notifications.
    
    This class provides an abstraction over the SMS sending service,
    allowing for easy switching between providers.
    """
    
    @classmethod
    @log_exceptions(log_level=logging.ERROR)
    def send_verification_code(cls, phone_number: str, code: str) -> bool:
        """
        Send a verification code via SMS.
        
        Args:
            phone_number: The phone number to send the code to (E.164 format)
            code: The verification code to send
            
        Returns:
            True if the SMS was sent successfully, False otherwise
        """
        # Get the SMS provider from settings
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'CONSOLE')
        
        # Choose the appropriate sending method based on the provider
        if sms_provider == 'TWILIO':
            return cls._send_via_twilio(phone_number, code)
        elif sms_provider == 'AFRICAS_TALKING':
            return cls._send_via_africas_talking(phone_number, code)
        else:
            # Default to console for development
            return cls._send_via_console(phone_number, code)
    
    @classmethod
    def _send_via_twilio(cls, phone_number: str, code: str) -> bool:
        """
        Send SMS using Twilio.
        
        Args:
            phone_number: The phone number to send to
            code: The verification code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import Twilio client only when needed
            from twilio.rest import Client
            
            # Get Twilio credentials from settings
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
            
            if not all([account_sid, auth_token, from_number]):
                raise ExternalServiceException(_("Twilio credentials not configured"))
            
            # Create Twilio client
            client = Client(account_sid, auth_token)
            
            # Prepare message content
            message_body = _("Your ClustR verification code is: {code}").format(code=code)
            
            # Send the message
            message = client.messages.create(
                body=message_body,
                from_=from_number,
                to=phone_number
            )
            
            logger.info(f"SMS sent via Twilio: {message.sid}")
            return True
            
        except ImportError:
            logger.error("Twilio package not installed")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS via Twilio: {str(e)}")
            raise ExternalServiceException(_("Failed to send SMS")) from e
    
    @classmethod
    def _send_via_africas_talking(cls, phone_number: str, code: str) -> bool:
        """
        Send SMS using Africa's Talking.
        
        Args:
            phone_number: The phone number to send to
            code: The verification code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import Africa's Talking SDK only when needed
            import africastalking
            
            # Get Africa's Talking credentials from settings
            username = getattr(settings, 'AFRICAS_TALKING_USERNAME', None)
            api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY', None)
            
            if not all([username, api_key]):
                raise ExternalServiceException(_("Africa's Talking credentials not configured"))
            
            # Initialize SDK
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            
            # Prepare message content
            message_body = _("Your ClustR verification code is: {code}").format(code=code)
            
            # Send the message
            response = sms.send(message_body, [phone_number])
            
            logger.info(f"SMS sent via Africa's Talking: {response}")
            return True
            
        except ImportError:
            logger.error("Africa's Talking package not installed")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS via Africa's Talking: {str(e)}")
            raise ExternalServiceException(_("Failed to send SMS")) from e
    
    @classmethod
    def _send_via_console(cls, phone_number: str, code: str) -> bool:
        """
        Log SMS to console (for development).
        
        Args:
            phone_number: The phone number to send to
            code: The verification code
            
        Returns:
            Always returns True
        """
        message = f"DEVELOPMENT MODE: SMS to {phone_number}: Your ClustR verification code is: {code}"
        logger.info(message)
        print(message)  # Print to console for easy visibility during development
        return True