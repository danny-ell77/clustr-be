"""
Shift Swap Request models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class ShiftSwapRequest(AbstractClusterModel):
    """
    Model for handling shift swap requests between staff members.
    """
    
    class SwapStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CANCELLED = "CANCELLED", _("Cancelled")
    
    original_shift = models.ForeignKey(
        verbose_name=_("original shift"),
        to="common.Shift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_original"
    )
    
    requested_by = models.ForeignKey(
        verbose_name=_("requested by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="shift_swap_requests"
    )
    
    requested_with = models.ForeignKey(
        verbose_name=_("requested with"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="shift_swap_offers"
    )
    
    target_shift = models.ForeignKey(
        verbose_name=_("target shift"),
        to="common.Shift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_target",
        null=True,
        blank=True,
        help_text=_("The shift to swap with (optional for coverage requests)")
    )
    
    reason = models.TextField(
        verbose_name=_("reason"),
        help_text=_("Reason for the swap request")
    )
    
    status = models.CharField(
        verbose_name=_("status"),
        max_length=20,
        choices=SwapStatus.choices,
        default=SwapStatus.PENDING
    )
    
    approved_by = models.ForeignKey(
        verbose_name=_("approved by"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_shift_swaps"
    )
    
    approved_at = models.DateTimeField(
        verbose_name=_("approved at"),
        null=True,
        blank=True
    )
    
    response_message = models.TextField(
        verbose_name=_("response message"),
        blank=True,
        help_text=_("Response message from the other staff member or admin")
    )
    
    class Meta:
        verbose_name = _("shift swap request")
        verbose_name_plural = _("shift swap requests")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Swap request: {self.original_shift.title} by {self.requested_by.name}"
    
    def approve(self, approved_by, response_message=""):
        """Approve the swap request."""
        if self.status != self.SwapStatus.PENDING:
            raise ValidationError(_("Can only approve pending requests"))
        
        self.status = self.SwapStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.response_message = response_message
        self.save(update_fields=["approved_by", "approved_at", "response_message"])
        
        # Perform the actual swap
        if self.target_shift:
            # Swap the assigned staff
            original_staff = self.original_shift.assigned_staff
            target_staff = self.target_shift.assigned_staff
            
            self.original_shift.assigned_staff = target_staff
            self.target_shift.assigned_staff = original_staff
            
            self.original_shift.save(update_fields=["assigned_staff"])
            self.target_shift.save(update_fields=["assigned_staff"])
        else:
            # Just reassign the original shift
            self.original_shift.assigned_staff = self.requested_with
            self.original_shift.save(update_fields=["assigned_staff"])
    
    def reject(self, rejected_by, response_message=""):
        """Reject the swap request."""
        if self.status != self.SwapStatus.PENDING:
            raise ValidationError(_("Can only reject pending requests"))
        
        self.status = self.SwapStatus.REJECTED
        self.approved_by = rejected_by
        self.approved_at = timezone.now()
        self.response_message = response_message
        self.save(update_fields=["approved_by", "approved_at", "response_message"])

