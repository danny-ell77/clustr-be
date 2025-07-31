"""
Task History models for ClustR application.
"""

import logging
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.common.models.base import AbstractClusterModel
from core.common.models.task.task import TaskStatus

# Related model imports (will be converted to string references)
# from core.common.models.task.task import TaskStatus

logger = logging.getLogger('clustr')


class TaskStatusHistory(AbstractClusterModel):
    """
    Model to track status changes for tasks.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    from_status = models.CharField(
        verbose_name=_("from status"),
        max_length=20,
        choices=TaskStatus.choices,
        null=True,
        blank=True,
        help_text=_("Previous status"),
    )

    to_status = models.CharField(
        verbose_name=_("to status"),
        max_length=20,
        choices=TaskStatus.choices,
        help_text=_("New status"),
    )

    changed_by = models.ForeignKey(
        verbose_name=_("changed by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_status_changes",
    )

    notes = models.TextField(
        verbose_name=_("notes"),
        blank=True,
        help_text=_("Notes about the status change"),
    )

    class Meta:
        default_permissions = []
        verbose_name = _("task status history")
        verbose_name_plural = _("task status histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task.task_number}: {self.from_status} → {self.to_status}"


class TaskEscalationHistory(AbstractClusterModel):
    """
    Model to track task escalations.
    """

    task = models.ForeignKey(
        verbose_name=_("task"),
        to="common.Task",
        on_delete=models.CASCADE,
        related_name="escalation_history",
    )

    escalated_to = models.ForeignKey(
        verbose_name=_("escalated to"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_escalations_received",
    )

    escalated_by = models.ForeignKey(
        verbose_name=_("escalated by"),
        to="accounts.AccountUser",
        on_delete=models.CASCADE,
        related_name="task_escalations_made",
    )

    reason = models.TextField(
        verbose_name=_("escalation reason"), help_text=_("Reason for escalation")
    )

    class Meta:
        default_permissions = []
        verbose_name = _("task escalation history")
        verbose_name_plural = _("task escalation histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task.task_number} escalated to {self.escalated_to.name}"

