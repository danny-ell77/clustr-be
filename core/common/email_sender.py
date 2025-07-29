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
    
    This enum has been cleaned up to only include notification types that are
    actively used by the new notification system and legacy authentication flows.
    """
    # Account notifications (still used by authentication system)
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    
    # Notification system email types (mapped from NotificationEvents)
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
    # Account notification templates (still used by authentication system)
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
    
    # Notification system email templates (mapped from NotificationEvents)
    NotificationTypes.EMERGENCY_ALERT: EmailTemplate(
        subject_template="ClustR - Emergency Alert",
        body_template="""
        EMERGENCY ALERT
        
        {{ alert_message }}
        
        Location: {{ location }}
        Time: {{ formatted_alert_time }}
        Severity: {{ severity }}
        
        Please take immediate action as required.
        
        The ClustR Team
        """
    ),
    
    NotificationTypes.VISITOR_ARRIVAL: EmailTemplate(
        subject_template="ClustR - Visitor Arrival Notification",
        body_template="""
        Hello {{ user_name }},
        
        Your visitor {{ visitor_name }} has arrived at the estate.
        
        {% if access_code %}Access Code: {{ access_code }}{% endif %}
        {% if formatted_arrival_time %}Arrival Time: {{ formatted_arrival_time }}{% endif %}
        {% if unit %}Unit: {{ unit }}{% endif %}
        
        Thank you,
        The ClustR Team
        """
    ),
    
    NotificationTypes.VISITOR_OVERSTAY: EmailTemplate(
        subject_template="ClustR - Visitor Overstay Alert",
        body_template="""
        Hello {{ user_name }},
        
        Your visitor {{ visitor_name }} has exceeded their scheduled visit duration.
        
        {% if access_code %}Access Code: {{ access_code }}{% endif %}
        {% if formatted_departure_time %}Expected Departure: {{ formatted_departure_time }}{% endif %}
        
        Please check on your visitor or update their visit duration if needed.
        
        Thank you,
        The ClustR Team
        """
    ),
    
    NotificationTypes.BILL_REMINDER: EmailTemplate(
        subject_template="ClustR - Bill Payment Reminder",
        body_template="""
        Hello {{ user_name }},
        
        This is a reminder that you have a bill due for payment:
        
        {% if bill_number %}Bill Number: {{ bill_number }}{% endif %}
        {% if bill_title %}Title: {{ bill_title }}{% endif %}
        {% if formatted_amount %}Amount: {{ formatted_amount }}{% endif %}
        {% if formatted_due_date %}Due Date: {{ formatted_due_date }}{% endif %}
        {% if bill_type %}Type: {{ bill_type }}{% endif %}
        
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
        
        {% if bill_number %}Bill Number: {{ bill_number }}{% endif %}
        {% if bill_title %}Bill Title: {{ bill_title }}{% endif %}
        {% if formatted_payment_amount %}Payment Amount: {{ formatted_payment_amount }}{% endif %}
        {% if transaction_id %}Transaction ID: {{ transaction_id }}{% endif %}
        {% if formatted_payment_date %}Payment Date: {{ formatted_payment_date }}{% endif %}
        
        {% if remaining_amount and remaining_amount > 0 %}
        Remaining Balance: {{ formatted_remaining_amount }}
        {% else %}
        This bill has been paid in full.
        {% endif %}
        
        {% if bill_status %}Bill Status: {{ bill_status }}{% endif %}
        
        Thank you for using ClustR!
        
        The ClustR Team
        """
    ),
    
    NotificationTypes.ANNOUNCEMENT: EmailTemplate(
        subject_template="ClustR - {{ announcement_title|default:'New Announcement' }}",
        body_template="""
        Hello {{ user_name }},
        
        {% if announcement_title %}{{ announcement_title }}{% endif %}
        
        {% if announcement_content %}
        {{ announcement_content }}
        {% endif %}
        
        {% if announcement_date %}
        Posted on: {{ announcement_date }}
        {% endif %}
        
        {% if author_name %}
        From: {{ author_name }}
        {% endif %}
        
        Thank you,
        The ClustR Team
        """
    ),
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