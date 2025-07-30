"""
Maintenance Cost models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class MaintenanceCost(AbstractClusterModel):
    """
    Model for tracking detailed maintenance costs.
    """

    maintenance_log = models.ForeignKey(
        verbose_name=_("maintenance log"),
        to="common.MaintenanceLog",
        on_delete=models.CASCADE,
        related_name="cost_breakdown",
    )

    category = models.CharField(
        verbose_name=_("cost category"),
        max_length=50,
        choices=[
            ("LABOR", _("Labor")),
            ("MATERIALS", _("Materials")),
            ("EQUIPMENT", _("Equipment")),
            ("CONTRACTOR", _("Contractor")),
            ("PERMITS", _("Permits")),
            ("OTHER", _("Other")),
        ],
        default="OTHER",
        help_text=_("Category of the cost"),
    )

    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        help_text=_("Description of the cost item"),
    )

    quantity = models.DecimalField(
        verbose_name=_("quantity"),
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text=_("Quantity of the item"),
    )

    unit_cost = models.DecimalField(
        verbose_name=_("unit cost"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Cost per unit"),
    )

    total_cost = models.DecimalField(
        verbose_name=_("total cost"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total cost (quantity × unit cost)"),
    )

    vendor = models.CharField(
        verbose_name=_("vendor"),
        max_length=200,
        blank=True,
        help_text=_("Vendor or supplier name"),
    )

    receipt_number = models.CharField(
        verbose_name=_("receipt number"),
        max_length=100,
        blank=True,
        help_text=_("Receipt or invoice number"),
    )

    date_incurred = models.DateField(
        verbose_name=_("date incurred"),
        default=timezone.now,
        help_text=_("Date when the cost was incurred"),
    )

    class Meta:
        verbose_name = _("maintenance cost")
        verbose_name_plural = _("maintenance costs")
        ordering = ["date_incurred"]

    def __str__(self):
        return f"{self.maintenance_log.maintenance_number} - {self.description}: ${self.total_cost}"

    def save(self, *args, **kwargs):
        """Override save to calculate total cost."""
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

