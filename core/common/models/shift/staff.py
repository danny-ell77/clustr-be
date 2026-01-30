"""
Staff model for on-site workers in Clusters
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from core.common.models.base import AbstractClusterModel
from core.common.models.shift.shift import ShiftType

logger = logging.getLogger('clustr')


class Staff(AbstractClusterModel):
    """
    Model representing on-site staff members (security, maintenance, cleaning, etc.).
    This is separate from AccountUser which represents dashboard users.
    """
    
    name = models.CharField(
        verbose_name=_("name"),
        max_length=200,
        help_text=_("Full name of the staff member")
    )
    
    email = models.EmailField(
        verbose_name=_("email"),
        blank=True,
        null=True,
        help_text=_("Email address for notifications (optional)")
    )
    
    phone_number = models.CharField(
        verbose_name=_("phone number"),
        max_length=20,
        help_text=_("Contact phone number")
    )
    
    staff_type = models.CharField(
        verbose_name=_("staff type"),
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.OTHER,
        help_text=_("Primary type of work this staff member performs")
    )
    
    employee_id = models.CharField(
        verbose_name=_("employee ID"),
        max_length=50,
        blank=True,
        help_text=_("Unique employee identifier")
    )
    
    is_active = models.BooleanField(
        verbose_name=_("is active"),
        default=True,
        help_text=_("Whether the staff member is currently active")
    )
    
    date_joined = models.DateField(
        verbose_name=_("date joined"),
        auto_now_add=True,
        help_text=_("Date when the staff member joined")
    )
    
    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Additional notes about the staff member")
    )
    
    class Meta:
        default_permissions = []
        verbose_name = _("staff member")
        verbose_name_plural = _("staff members")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["staff_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["cluster", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cluster', 'employee_id'],
                condition=models.Q(employee_id__isnull=False) & ~models.Q(employee_id=''),
                name='unique_employee_id_per_cluster'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_staff_type_display()})"
    
    def clean(self):
        """Validate staff data."""
        super().clean()
        
        if not self.phone_number and not self.email:
            raise ValidationError(_("At least one contact method (phone or email) is required"))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def contact_info(self):
        """Get primary contact information."""
        return self.phone_number or self.email
    
    def get_assigned_shifts_count(self, status=None):
        """Get count of assigned shifts, optionally filtered by status."""
        from core.common.models.shift.shift import Shift
        
        shifts = Shift.objects.filter(cluster=self.cluster, assigned_staff=self)
        if status:
            shifts = shifts.filter(status=status)
        return shifts.count()
