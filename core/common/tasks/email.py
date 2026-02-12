import logging
from typing import Iterable

from celery import shared_task
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


@shared_task(
    ignore_result=True,  # We have no need for the result
    name="send_account_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    serializer="pickle",
)
def send_account_email(email_messages: Iterable[EmailMessage]):
    # TODO: Add a callback with the email content as an argument of type SentEmailContent
    fail_silently = not settings.DEBUG
    with mail.get_connection(fail_silently=fail_silently) as connection:
        connection.send_messages(email_messages)
