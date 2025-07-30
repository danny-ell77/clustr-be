"""
Child models for ClustR application.
"""

import logging
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

# Related model imports (will be converted to string references)
# from core.common.models.child.unknown import Gender

logger = logging.getLogger('clustr')


class Child(AbstractClusterModel):
    """
    Model for managing children/wards in the estate.
    """

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")

    name = models.CharField(
        verbose_name=_("child name"),
        max_length=100,
        help_text=_("Full name of the child"),
    )

    date_of_birth = models.DateField(
        verbose_name=_("date of birth"),
        help_text=_("Date of birth of the child"),
    )

    gender = models.CharField(
        verbose_name=_("gender"),
        max_length=10,
        choices=Gender.choices,
        help_text=_("Gender of the child"),
    )

    profile_photo = models.URLField(
        verbose_name=_("profile photo"),
        max_length=500,
        blank=True,
        null=True,
        help_text=_("URL to the child's profile photo"),
    )

    house_number = models.CharField(
        verbose_name=_("house number"),
        max_length=20,
        help_text=_("House/unit number where the child lives"),
    )

    parent = models.ForeignKey(
        verbose_name=_("parent/guardian"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="children",
        help_text=_("Parent or guardian of the child"),
    )

    emergency_contacts = models.JSONField(
        verbose_name=_("emergency contacts"),
        default=list,
        help_text=_("List of emergency contact information"),
    )

    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether the child is currently active in the system"),
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the child"),
    )

    class Meta:
        verbose_name = _("Child")
        verbose_name_plural = _("Children")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["cluster", "parent"]),
            models.Index(fields=["cluster", "is_active"]),
            models.Index(fields=["cluster", "house_number"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.parent.name})"

    @property
    def age(self):
        """Calculate the child's age in years"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def get_emergency_contacts_display(self):
        """Get formatted emergency contacts"""
        if not self.emergency_contacts:
            return []
        
        return [
            {
                'name': contact.get('name', ''),
                'phone': contact.get('phone', ''),
                'relationship': contact.get('relationship', ''),
            }
            for contact in self.emergency_contacts
        ]

