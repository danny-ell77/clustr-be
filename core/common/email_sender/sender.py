import logging

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.template import Template
from django.template.loader import get_template
from django.utils.safestring import SafeString

from core.common import tasks
from core.common.email_sender.email_attributes import DEFAULT_EMAIL_ATTRIBUTES
from core.common.email_sender.types import (
    ClustRGenericNotification,
    NotificationTypes,
    TransactionalEmail,
)

logger = logging.getLogger(__name__)


class AccountEmailSender:
    def __init__(self, recipients, email_type, **kwargs):
        self.options = kwargs
        self.recipients: list[str] = recipients
        self.email_type: NotificationTypes = email_type

    def send(self):
        default_attribute = DEFAULT_EMAIL_ATTRIBUTES.get(self.email_type)
        required_attributes = ["template_name", "subject", "context"]
        required_attributes_present = all(
            self.options.get(attr) for attr in required_attributes
        )
        if default_attribute is None and not required_attributes_present:
            raise ValueError(
                f"At least one of the following required parameters is missing: {', '.join(required_attributes)}"
            )

        transactional_email = self._get_email_content(
            self.recipients, default_attribute, self.options
        )

        email_message = self._build_email_message(transactional_email)

        self._send_messages([email_message])

    def send_to_many(self, contexts: dict):
        messages = []
        defaults = DEFAULT_EMAIL_ATTRIBUTES.get(self.email_type)
        for email_address in self.recipients:
            context = contexts.get(email_address)
            if context:
                message = self._build_email_message(
                    self._get_email_content(
                        recipients=[email_address],
                        default_attribute=defaults,
                        kwargs={
                            "context": context,
                        },
                    )
                )
                messages.append(message)
        self._send_messages(messages)

    def _get_email_content(self, recipients, default_attribute, kwargs: dict):
        return TransactionalEmail(
            from_name=kwargs.setdefault("from_name", ClustRGenericNotification.name),
            from_email_address=getattr(settings, "DEFAULT_FROM_EMAIL", "info@smuite.com"),
            to_emails=recipients,
            subject=kwargs.setdefault("subject", default_attribute.subject),
            body=get_template(template_name=default_attribute.template_name).template,
            context=kwargs.setdefault("context", default_attribute.context),
            attachments=kwargs.setdefault("attachments", None),
            preheader=kwargs.setdefault("preheader", ""),
        )

    def _build_email_message(self, transactional_email) -> EmailMessage:
        rendered_subject, rendered_body = self._render_email_content(
            transactional_email
        )
        sender = f"{transactional_email.from_name} <{transactional_email.from_email_address}>"
        email_message = EmailMessage(
            subject=rendered_subject,
            body=rendered_body,
            from_email=sender,
            to=transactional_email.to_emails,
            reply_to=transactional_email.reply_to_email_address,
            headers=transactional_email.headers,
            attachments=transactional_email.attachments,
        )
        email_message.content_subtype = "html"
        return email_message

    def _render_email_content(self, transactional_email):
        context = transactional_email.context
        subject_template = transactional_email.subject
        if isinstance(subject_template, str):
            subject_template = Template(template_string=transactional_email.subject)
        body_template = transactional_email.body
        if isinstance(body_template, str):
            body_template = Template(template_string=transactional_email.body)

        _rendered_subject = subject_template.render(context=context)
        _rendered_body = body_template.render(context=context)
        self._add_preheader(transactional_email, _rendered_body)
        return _rendered_subject, _rendered_body

    def _add_preheader(self, transactional_email, body: SafeString) -> str:
        """Injects the preheader text into the email body HTML"""
        if not transactional_email.preheader:
            return body

        preheader_html = (
            '<span style="display:none !important; visibility:hidden; mso-hide:all; font-size:1px; '
            'color:#ffffff;line-height:1px; max-height:0px; max-width:0px; opacity:0; overflow:hidden;">'
            f"{transactional_email.preheader}"
            "</span>"
        )
        try:
            body_tag = "<body>"
            body_tag_start = body.index(body_tag)
            return body[:body_tag_start] + preheader_html + body[body_tag_start:]
        except ValueError:
            raise Exception("Invalid 'body' tag in email HTML")

    def _send_messages(self, email_messages):
        """
        Attempts async delivery via Celery first. Falls back to synchronous
        SMTP when Celery/Redis is unavailable (e.g. local dev without Docker).
        SMTP errors in DEBUG mode are logged instead of crashing the request.
        """
        if not settings.DEBUG:
            tasks.send_account_email.apply_async(email_messages, serializer="pickle")
            return

        try:
            tasks.send_account_email.apply_async(email_messages, serializer="pickle")
        except Exception:
            logger.info("Celery unavailable, falling back to synchronous SMTP")
            try:
                with mail.get_connection(fail_silently=False) as connection:
                    connection.send_messages(email_messages)
            except Exception as smtp_err:
                logger.error("SMTP send failed: %s", smtp_err, exc_info=True)
