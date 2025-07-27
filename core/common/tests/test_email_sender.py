from django.conf import settings
from django.core import mail
from django.template import Context, Template
from django.template.loader import get_template
from django.test import TestCase

from core.common.email_sender import (
    DEFAULT_EMAIL_ATTRIBUTES,
    AccountEmailSender,
    NotificationTypes,
)


class TestAccountEmailSender(TestCase):
    def setUp(self):
        self.recipients = ["test@example.com"]
        self.email_type = NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET
        self.kwargs = {
            "template_name": "onboarding_otp_password_reset.html",
            "subject": "Account Created",
            "context": Context(dict_={"name": "John Doe"}),
        }
        settings.DEBUG = True

    def test_send_email_with_default_attributes(self):
        sender = AccountEmailSender(self.recipients, self.email_type)
        sender.send()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.subject, DEFAULT_EMAIL_ATTRIBUTES[self.email_type].subject
        )
        email_template = get_template(
            DEFAULT_EMAIL_ATTRIBUTES[self.email_type].template_name
        ).template
        self.assertEqual(
            email.body,
            Template(email_template).render(
                DEFAULT_EMAIL_ATTRIBUTES[self.email_type].context
            ),
        )

    def test_send_email_with_custom_attributes(self):
        sender = AccountEmailSender(self.recipients, self.email_type, **self.kwargs)
        sender.send()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, self.kwargs["subject"])
        email_template = get_template(self.kwargs["template_name"]).template
        self.assertEqual(
            email.body, str(Template(email_template).render(self.kwargs["context"]))
        )

    def test_send_email_with_missing_required_attributes(self):
        invalid_kwargs = {
            "subject": "Account Created",
            "context": Context(dict_={"name": "John Doe"}),
        }
        sender = AccountEmailSender(
            self.recipients, "INVALID_NOTIFICATION_TYPE", **invalid_kwargs
        )
        with self.assertRaises(ValueError):
            sender.send()

    def test_add_preheader(self):
        sender = AccountEmailSender(self.recipients, self.email_type, **self.kwargs)
        self.kwargs.update({"preheader": "<p>Hello</p>"})
        transactional_email = sender._get_email_content(
            self.recipients, DEFAULT_EMAIL_ATTRIBUTES[self.email_type], self.kwargs
        )
        body_with_preheader = sender._add_preheader(
            transactional_email, "<body>Test email body</body>"
        )
        self.assertIn(transactional_email.preheader, body_with_preheader)

    def test_add_preheader_with_invalid_body(self):
        sender = AccountEmailSender(self.recipients, self.email_type, **self.kwargs)
        self.kwargs.update({"preheader": "<p>Hello</p>"})
        transactional_email = sender._get_email_content(
            self.recipients, DEFAULT_EMAIL_ATTRIBUTES[self.email_type], self.kwargs
        )
        with self.assertRaises(Exception):
            sender._add_preheader(transactional_email, "Invalid email body")
