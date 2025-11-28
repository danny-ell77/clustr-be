"""
Cluster models for ClustR application.
"""
from typing import TYPE_CHECKING
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models import UUIDPrimaryKey, ObjectHistoryTracker

if TYPE_CHECKING:
    from accounts.models.users import AccountUser

class Cluster(UUIDPrimaryKey, ObjectHistoryTracker):
    """
    Cluster model representing a property cluster in the ClustR system.
    This is the primary entity for multi-tenant architecture.
    Clusters can be estates, facilities, or other property groupings.
    """

    class Types(models.TextChoices):
        ESTATE = "ESTATE", _("Estate")
        FACILITY = "FACILITY", _("Facility")
        COMMERCIAL = "COMMERCIAL", _("Commercial")
        MIXED_USE = "MIXED_USE", _("Mixed Use")

    name = models.CharField(
        verbose_name=_("cluster name"),
        max_length=255,
        help_text=_("Name of the cluster"),
    )
    type = models.CharField(
        verbose_name=_("cluster type"),
        max_length=20,
        choices=Types.choices,
        default=Types.ESTATE,
        help_text=_("Type of property cluster"),
    )
    address = models.TextField(
        verbose_name=_("address"), help_text=_("Physical address of the cluster")
    )
    city = models.CharField(
        verbose_name=_("city"),
        max_length=100,
        help_text=_("City where the cluster is located"),
    )
    state = models.CharField(
        verbose_name=_("state"),
        max_length=100,
        help_text=_("State where the cluster is located"),
    )
    country = models.CharField(
        verbose_name=_("country"),
        max_length=100,
        help_text=_("Country where the cluster is located"),
    )
    logo_url = models.URLField(
        verbose_name=_("logo URL"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("URL to the cluster's logo image"),
    )
    primary_contact_name = models.CharField(
        verbose_name=_("primary contact name"),
        max_length=255,
        help_text=_("Name of the primary contact person for the cluster"),
    )
    primary_contact_email = models.EmailField(
        verbose_name=_("primary contact email"),
        help_text=_("Email address of the primary contact person"),
    )
    primary_contact_phone = models.CharField(
        verbose_name=_("primary contact phone"),
        max_length=20,
        help_text=_("Phone number of the primary contact person"),
    )
    subscription_status = models.CharField(
        verbose_name=_("subscription status"),
        max_length=20,
        choices=[
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("trial", _("Trial")),
        ],
        default="trial",
        help_text=_("Current subscription status of the cluster"),
    )
    subscription_expiry = models.DateTimeField(
        verbose_name=_("subscription expiry"),
        null=True,
        blank=True,
        help_text=_("Date and time when the current subscription expires"),
    )
    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether this cluster is active in the system"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("cluster")
        verbose_name_plural = _("clusters")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["type"]),
            models.Index(fields=["city"]),
            models.Index(fields=["subscription_status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}, {self.city})"
    
    def get_all_users(self):
        """Get all users in this cluster."""
        return self.users.all()

    def add_admin(self, admin: "AccountUser"):
        """
        Add an admin to this cluster.
        There should be some logic though to figure out  which clustr to set as primary.
        Currently the primary cluster is set to the latest cluster added.
        """
        admin.primary_cluster = self
        admin.cluster.add(self)
        admin.save(update_fields=["primary_cluster"])
