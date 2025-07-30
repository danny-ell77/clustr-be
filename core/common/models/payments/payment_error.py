"""
Payment Error models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class PaymentErrorType(models.TextChoices):
    """Payment error type choices"""

    INSUFFICIENT_FUNDS = "insufficient_funds", _("Insufficient Funds")
    INVALID_CARD = "invalid_card", _("Invalid Card")
    EXPIRED_CARD = "expired_card", _("Expired Card")
    DECLINED_CARD = "declined_card", _("Declined Card")
    NETWORK_ERROR = "network_error", _("Network Error")
    PROVIDER_ERROR = "provider_error", _("Provider Error")
    VALIDATION_ERROR = "validation_error", _("Validation Error")
    TIMEOUT_ERROR = "timeout_error", _("Timeout Error")
    AUTHENTICATION_ERROR = "authentication_error", _("Authentication Error")
    LIMIT_EXCEEDED = "limit_exceeded", _("Limit Exceeded")
    ACCOUNT_SUSPENDED = "account_suspended", _("Account Suspended")
    UNKNOWN_ERROR = "unknown_error", _("Unknown Error")
    # Utility-specific errors
    UTILITY_PROVIDER_ERROR = "utility_provider_error", _("Utility Provider Error")
    INVALID_CUSTOMER_ID = "invalid_customer_id", _("Invalid Customer ID")
    UTILITY_SERVICE_UNAVAILABLE = "utility_service_unavailable", _(
        "Utility Service Unavailable"
    )
    METER_NOT_FOUND = "meter_not_found", _("Meter Not Found")
    CUSTOMER_VALIDATION_FAILED = "customer_validation_failed", _(
        "Customer Validation Failed"
    )


class PaymentErrorSeverity(models.TextChoices):
    """Payment error severity choices"""

    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class PaymentError(AbstractClusterModel):
    """
    Payment error model for tracking transaction failures and providing user-friendly audit trails.
    """

    transaction = models.ForeignKey('Transaction',
        on_delete=models.CASCADE,
        related_name="payment_errors",
        verbose_name=_("transaction"),
        help_text=_("The transaction that failed"),
    )

    error_type = models.CharField(
        verbose_name=_("error type"),
        max_length=30,
        choices=PaymentErrorType.choices,
        help_text=_("Categorized error type"),
    )

    severity = models.CharField(
        verbose_name=_("severity"),
        max_length=20,
        choices=PaymentErrorSeverity.choices,
        help_text=_("Error severity level"),
    )

    provider_error_code = models.CharField(
        verbose_name=_("provider error code"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Error code from payment provider"),
    )

    provider_error_message = models.TextField(
        verbose_name=_("provider error message"),
        help_text=_("Original error message from payment provider"),
    )

    user_friendly_message = models.TextField(
        verbose_name=_("user friendly message"),
        help_text=_("User-friendly error message"),
    )

    recovery_options = models.JSONField(
        verbose_name=_("recovery options"),
        blank=True,
        null=True,
        help_text=_("Available recovery options for the user"),
    )

    retry_count = models.PositiveIntegerField(
        verbose_name=_("retry count"),
        default=0,
        help_text=_("Number of retry attempts made"),
    )

    max_retries = models.PositiveIntegerField(
        verbose_name=_("max retries"),
        default=3,
        help_text=_("Maximum number of retry attempts allowed"),
    )

    can_retry = models.BooleanField(
        verbose_name=_("can retry"),
        default=True,
        help_text=_("Whether this error allows retry attempts"),
    )

    is_resolved = models.BooleanField(
        verbose_name=_("is resolved"),
        default=False,
        help_text=_("Whether this error has been resolved"),
    )

    resolved_at = models.DateTimeField(
        verbose_name=_("resolved at"),
        null=True,
        blank=True,
        help_text=_("Date and time when error was resolved"),
    )

    resolution_method = models.CharField(
        verbose_name=_("resolution method"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Method used to resolve the error"),
    )

    admin_notified = models.BooleanField(
        verbose_name=_("admin notified"),
        default=False,
        help_text=_("Whether administrators have been notified"),
    )

    user_notified = models.BooleanField(
        verbose_name=_("user notified"),
        default=False,
        help_text=_("Whether user has been notified"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional error metadata"),
    )

    class Meta:
        verbose_name = _("Payment Error")
        verbose_name_plural = _("Payment Errors")
        indexes = [
            models.Index(fields=["transaction", "created_at"]),
            models.Index(fields=["error_type"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["can_retry", "retry_count"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment Error: {self.error_type} - {self.transaction.transaction_id}"

    def can_be_retried(self):
        """Check if this error can be retried."""
        return (
            self.can_retry
            and self.retry_count < self.max_retries
            and not self.is_resolved
        )

    def increment_retry_count(self):
        """Increment the retry count."""
        self.retry_count += 1
        self.save(update_fields=["retry_count"])

    def mark_as_resolved(self, resolution_method=None):
        """Mark the error as resolved."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if resolution_method:
            self.resolution_method = resolution_method
        self.save(update_fields=["is_resolved", "resolved_at", "resolution_method"])

    def get_next_retry_delay(self):
        """Get the delay before next retry attempt in minutes."""
        # Exponential backoff: 2, 4, 8 minutes
        return min(2**self.retry_count, 30)  # Cap at 30 minutes

