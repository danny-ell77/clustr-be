 """
Email sending functionality for ClustR application.
"""

import logging
from enum import Enum
from typing import List, Optional, Dict, Any

from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _

from core.common.error_utils import log_exceptions

logger = logging.getLogger('clustr')


class NotificationTypes(str, Enum):
    """
    Types of email notifications that can be sent.
    """
    # Authentication notifications
    ONBOARDING_OTP_PASSWORD_RESET = "ONBOARDING_OTP_PASSWORD_RESET"
    ONBOARDING_TOKEN_PASSWORD_RESET = "ONBOARDING_TOKEN_PASSWORD_RESET"
    OTP_PASSWORD_RESET = "OTP_PASSWORD_RESET"
    WEB_TOKEN_PASSWORD_RESET = "WEB_TOKEN_PASSWORD_RESET"
    RESEND_OTP = "RESEND_OTP"
    RESEND_WEB_TOKEN = "RESEND_WEB_TOKEN"
    NEW_ADMIN_ONBOARDING = "NEW_ADMIN_ONBOARDING"
    NEW_SUBUSER_ACCOUNT_TO_OWNER = "NEW_SUBUSER_ACCOUNT_TO_OWNER"
    
    # Verification notifications
    EMAIL_VERIFICATION_OTP = "EMAIL_VERIFICATION_OTP"
    EMAIL_VERIFICATION_TOKEN = "EMAIL_VERIFICATION_TOKEN"
    PHONE_VERIFICATION_OTP = "PHONE_VERIFICATION_OTP"
    PROFILE_UPDATE_OTP = "PROFILE_UPDATE_OTP"
    PROFILE_UPDATE_TOKEN = "PROFILE_UPDATE_TOKEN"
    
    # Account notifications
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    
    # Other notifications
    ANNOUNCEMENT = "ANNOUNCEMENT"
    VISITOR_ARRIVAL = "VISITOR_ARRIVAL"
    VISITOR_OVERSTAY = "VISITOR_OVERSTAY"
    EMERGENCY_ALERT = "EMERGENCY_ALERT"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"
    BILL_REMINDER = "BILL_REMINDER"
    
    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class EmailTemplate:
    """
    Email template configuration.
    """
    def __init__(
        self,
        subject_template: str,
        body_template: str,
        html_template: Optional[str] = None
    ):
        self.subject_template = subject_template
        self.body_template = body_template
        self.html_template = html_template


# Email templates for different notification types
EMAIL_TEMPLATES = {
    NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET: EmailTemplate(
        subject_template="Welcome to ClustR - Verify Your Account",
        body_template="""
        Hello {{ user.name }},
        
        Welcome to ClustR! To complete your registration, please use the following verification code:
        
        {{ otp }}
        
        This code will expire in 2 hours.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.ONBOARDING_TOKEN_PASSWORD_RESET: EmailTemplate(
        subject_template="Welcome to ClustR - Verify Your Account",
        body_template="""
        Hello {{ user.name }},
        
        Welcome to ClustR! To complete your registration, please click the link below:
        
        {{ verification_url }}?token={{ token }}
        
        This link will expire in 2 hours.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.OTP_PASSWORD_RESET: EmailTemplate(
        subject_template="ClustR - Password Reset Code",
        body_template="""
        Hello {{ user.name }},
        
        You requested a password reset. Please use the following code to reset your password:
        
        {{ otp }}
        
        This code will expire in 2 hours.
        
        If you did not request this password reset, please ignore this email.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.WEB_TOKEN_PASSWORD_RESET: EmailTemplate(
        subject_template="ClustR - Password Reset Link",
        body_template="""
        Hello {{ user.name }},
        
        You requested a password reset. Please click the link below to reset your password:
        
        {{ reset_url }}?token={{ token }}
        
        This link will expire in 2 hours.
        
        If you did not request this password reset, please ignore this email.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.EMAIL_VERIFICATION_OTP: EmailTemplate(
        subject_template="ClustR - Verify Your Email Address",
        body_template="""
        Hello {{ user.name }},
        
        Please use the following code to verify your email address:
        
        {{ otp }}
        
        This code will expire in 2 hours.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.EMAIL_VERIFICATION_TOKEN: EmailTemplate(
        subject_template="ClustR - Verify Your Email Address",
        body_template="""
        Hello {{ user.name }},
        
        Please click the link below to verify your email address:
        
        {{ verification_url }}?token={{ token }}
        
        This link will expire in 2 hours.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.PROFILE_UPDATE_OTP: EmailTemplate(
        subject_template="ClustR - Verify Profile Changes",
        body_template="""
        Hello {{ user.name }},
        
        You recently requested to update your profile information. Please use the following code to confirm these changes:
        
        {{ otp }}
        
        This code will expire in 2 hours.
        
        If you did not request these changes, please contact support immediately.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.ACCOUNT_LOCKED: EmailTemplate(
        subject_template="ClustR - Account Security Alert",
        body_template="""
        Hello {{ user.name }},
        
        Your ClustR account has been temporarily locked due to multiple failed login attempts.
        
        Your account will be automatically unlocked after {{ lockout_duration }} minutes, or you can contact support for assistance.
        
        If you did not attempt to log in, please contact support immediately as your account may be at risk.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.PASSWORD_CHANGED: EmailTemplate(
        subject_template="ClustR - Password Changed",
        body_template="""
        Hello {{ user.name }},
        
        Your ClustR account password was recently changed.
        
        If you made this change, you can ignore this email.
        
        If you did not change your password, please contact support immediately.
        
        Thank you,
        The ClustR Team
        """
    ),
    # Visitor notification templates
    NotificationTypes.VISITOR_ARRIVAL: EmailTemplate(
        subject_template="ClustR - Visitor Arrival Notification",
        body_template="""
        Hello,
        
        Your visitor {{ visitor_name }} has arrived at the estate.
        
        Access Code: {{ access_code }}
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.VISITOR_OVERSTAY: EmailTemplate(
        subject_template="ClustR - Visitor Overstay Alert",
        body_template="""
        Hello,
        
        Your visitor {{ visitor_name }} has exceeded their scheduled visit duration.
        
        Access Code: {{ access_code }}
        
        Please check on your visitor or update their visit duration if needed.
        
        Thank you,
        The ClustR Team
        """
    ),
    # Bill notification templates
    NotificationTypes.BILL_REMINDER: EmailTemplate(
        subject_template="ClustR - Bill Payment Reminder",
        body_template="""
        Hello {{ user_name }},
        
        This is a reminder that you have a bill due for payment:
        
        Bill Number: {{ bill_number }}
        Title: {{ bill_title }}
        Amount: {{ currency }} {{ bill_amount }}
        Due Date: {{ due_date }}
        Type: {{ bill_type }}
        
        {% if days_until_due %}
        This bill is due in {{ days_until_due }} day(s).
        {% endif %}
        
        {% if days_overdue %}
        This bill is {{ days_overdue }} day(s) overdue.
        {% endif %}
        
        Please log in to your ClustR account to make payment.
        
        Thank you,
        The ClustR Team
        """
    ),
    NotificationTypes.PAYMENT_RECEIPT: EmailTemplate(
        subject_template="ClustR - Payment Receipt",
        body_template="""
        Hello {{ user_name }},
        
        Thank you for your payment. Here are the details:
        
        Bill Number: {{ bill_number }}
        Bill Title: {{ bill_title }}
        Payment Amount: {{ currency }} {{ payment_amount }}
        Transaction ID: {{ transaction_id }}
        Payment Date: {{ payment_date }}
        
        {% if remaining_amount > 0 %}
        Remaining Balance: {{ currency }} {{ remaining_amount }}
        {% else %}
        This bill has been paid in full.
        {% endif %}
        
        Bill Status: {{ bill_status }}
        
        Thank you for using ClustR!
        
        The ClustR Team
        """
    ),
    # Add templates for other notification types as needed
}


class AccountEmailSender:
    """
    Handles sending emails for account-related notifications.
    """
    
    def __init__(
        self,
        recipients: List[str],
        email_type: NotificationTypes,
        context: Context,
        from_email: Optional[str] = None
    ):
        self.recipients = recipients
        self.email_type = email_type
        self.context = context
        self.from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@clustr.app')
    
    @log_exceptions(log_level=logging.ERROR)
    def send(self) -> bool:
        """
        Send the email notification.
        
        Returns:
            True if the email was sent successfully, False otherwise
        """
        # Get the template for this notification type
        template = EMAIL_TEMPLATES.get(self.email_type)
        if not template:
            logger.error(f"No template found for notification type: {self.email_type}")
            return False
        
        # Render the subject and body templates
        subject = Template(template.subject_template).render(self.context)
        body = Template(template.body_template).render(self.context)
        
        # Render HTML template if available
        html_message = None
        if template.html_template:
            html_message = Template(template.html_template).render(self.context)
        
        # Send the email
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=self.from_email,
                recipient_list=self.recipients,
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(
                f"Email sent: {self.email_type}",
                extra={
                    'recipients': self.recipients,
                    'email_type': self.email_type
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send email: {str(e)}",
                extra={
                    'recipients': self.recipients,
                    'email_type': self.email_type,
                    'error': str(e)
                }
            )
            
            return False