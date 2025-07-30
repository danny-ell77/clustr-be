import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from core.common.models.base import AbstractClusterModel
from core.common.models.payments.bill import BillType
from core.common.models.payments.transaction import PaymentProvider


logger = logging.getLogger('clustr')

class UtilityProvider(AbstractClusterModel):
    """
    Utility provider model for managing external utility service providers.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        help_text=_("Utility provider name"),
    )

    provider_type = models.CharField(
        verbose_name=_("provider type"),
        max_length=20,
        choices=BillType.choices,
        help_text=_("Type of utility service provided"),
    )

    api_provider = models.CharField(
        verbose_name=_("API provider"),
        max_length=20,
        choices=PaymentProvider.choices,
        help_text=_("Payment API provider (Paystack/Flutterwave)"),
    )

    provider_code = models.CharField(
        verbose_name=_("provider code"),
        max_length=50,
        help_text=_("Unique provider code for API calls (e.g., 'ikeja-electric')"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether this provider is currently active"),
    )

    supports_validation = models.BooleanField(
        verbose_name=_("supports validation"),
        default=True,
        help_text=_("Whether this provider supports customer validation"),
    )

    supports_info_lookup = models.BooleanField(
        verbose_name=_("supports info lookup"),
        default=True,
        help_text=_("Whether this provider supports customer info lookup"),
    )

    minimum_amount = models.DecimalField(
        verbose_name=_("minimum amount"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Minimum payment amount"),
    )

    maximum_amount = models.DecimalField(
        verbose_name=_("maximum amount"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("100000.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Maximum payment amount"),
    )

    metadata = models.JSONField(
        verbose_name=_("metadata"),
        blank=True,
        null=True,
        help_text=_("Additional provider metadata and configuration"),
    )

    class Meta:
        verbose_name = _("Utility Provider")
        verbose_name_plural = _("Utility Providers")
        unique_together = [["provider_code", "api_provider", "cluster"]]
        indexes = [
            models.Index(fields=["provider_type", "cluster"]),
            models.Index(fields=["api_provider"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"

    def is_amount_valid(self, amount):
        """Check if the payment amount is within provider limits."""
        return self.minimum_amount <= amount <= self.maximum_amount
