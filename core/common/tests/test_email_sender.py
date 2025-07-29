from django.conf import settings
from django.core import mail
from django.template import Context
from django.test import TestCase

from core.common.email_sender import (
    AccountEmailSender,
    NotificationTypes,
    EMAIL_TEMPLATES,
)


class TestAccountEmailSender(TestCase):
    def setUp(self):
        self.recipients = ["test@example.com"]
        self.email_type = NotificationTypes.PASSWORD_CHANGED
        self.context = Context(dict_={"user": {"name": "John Doe"}})
        settings.DEBUG = True

    def test_send_email_with_valid_notification_type(self):
        """Test sending email with a valid notification type."""
        sender = AccountEmailSender(
            recipients=self.recipients,
            email_type=self.email_type,
            context=self.context
        )
        result = sender.send()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        template = EMAIL_TEMPLATES[self.email_type]
        self.assertEqual(email.subject, template.subject_template)
        self.assertIn("John Doe", email.body)

    def test_send_email_with_visitor_arrival_type(self):
        """Test sending visitor arrival notification."""
        email_type = NotificationTypes.VISITOR_ARRIVAL
        context = Context(dict_={
            "user_name": "Jane Smith",
            "visitor_name": "John Visitor",
            "access_code": "ABC123",
            "unit": "A101"
        })
        
        sender = AccountEmailSender(
            recipients=self.recipients,
            email_type=email_type,
            context=context
        )
        result = sender.send()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn("Visitor Arrival", email.subject)
        self.assertIn("John Visitor", email.body)
        self.assertIn("ABC123", email.body)

    def test_send_email_with_emergency_alert_type(self):
        """Test sending emergency alert notification."""
        email_type = NotificationTypes.EMERGENCY_ALERT
        context = Context(dict_={
            "alert_message": "Fire alarm activated",
            "location": "Building A",
            "severity": "HIGH",
            "formatted_alert_time": "14:30 on January 15, 2024"
        })
        
        sender = AccountEmailSender(
            recipients=self.recipients,
            email_type=email_type,
            context=context
        )
        result = sender.send()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn("Emergency Alert", email.subject)
        self.assertIn("Fire alarm activated", email.body)
        self.assertIn("Building A", email.body)

    def test_send_email_with_invalid_notification_type(self):
        """Test sending email with invalid notification type returns False."""
        sender = AccountEmailSender(
            recipients=self.recipients,
            email_type="INVALID_TYPE",
            context=self.context
        )
        result = sender.send()
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_email_with_multiple_recipients(self):
        """Test sending email to multiple recipients."""
        recipients = ["test1@example.com", "test2@example.com"]
        sender = AccountEmailSender(
            recipients=recipients,
            email_type=self.email_type,
            context=self.context
        )
        result = sender.send()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, recipients)
