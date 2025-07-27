"""
Payment webhook URL configuration.
"""

from django.urls import path
from core.common.views.payment_webhooks import (
    paystack_webhook,
    flutterwave_webhook,
    verify_payment,
)

urlpatterns = [
    path('webhooks/paystack/', paystack_webhook, name='paystack-webhook'),
    path('webhooks/flutterwave/', flutterwave_webhook, name='flutterwave-webhook'),
    path('verify-payment/', verify_payment, name='verify-payment'),
]