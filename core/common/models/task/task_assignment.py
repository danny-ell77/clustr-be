"""
Task Assignment models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel

logger = logging.getLogger('clustr')


class TaskAssignment(AbstractClusterModel):
    """
    Model for tracking task assignments and reassignments.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )

    assigned_by = models.ForeignKey(
        verbose_name=_("assigned by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments_made",
    )

    assigned_at = models.DateTimeField(verbose_name=_("assigned at"), auto_now_add=True)

    notes = models.TextField(
        verbose_name=_("assignment notes"),
        blank=True,
        help_text=_("Notes about the assignment"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("task assignment")
        verbose_name_plural = _("task assignments")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.task.task_number} assigned to {self.assigned_to.name}"


class TaskAssignmentHistory(AbstractClusterModel):
    """
    Model for tracking task assignment history.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="assignment_history",
    )

    assigned_from = models.ForeignKey(
        verbose_name=_("assigned from"),
        to="accounts.AccountUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_assignments_from",
    )

    assigned_to = models.ForeignKey(
        verbose_name=_("assigned to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignments_to",
    )

    assigned_by = models.ForeignKey(
        verbose_name=_("assigned by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_assignment_actions",
    )

    class Meta:
        default_permissions = []
        verbose_name = _("task assignment history")
        verbose_name_plural = _("task assignment histories")
        ordering = ["-created_at"]

    def __str__(self):
        if self.assigned_from:
            return f"{self.task.task_number}: {self.assigned_from.name} → {self.assigned_to.name}"
        return f"{self.task.task_number}: assigned to {self.assigned_to.name}"

