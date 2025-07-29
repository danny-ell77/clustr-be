"""
Notification channels package for ClustR notification system.

This package contains the base notification channel interface and
concrete implementations for different delivery methods.
"""

from .base import BaseNotificationChannel
from .sms import SmsChannel

__all__ = ['BaseNotificationChannel', 'SmsChannel']