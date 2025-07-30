import logging
from typing import TYPE_CHECKING, Optional, cast
from uuid import UUID

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.common.email_sender import TransactionalEmail
from core.common.models import ObjectHistoryTracker, UUIDPrimaryKey

if TYPE_CHECKING:
    from accounts.models import AccountUser

logger = logging.getLogger(__name__)


class BaseTask(UUIDPrimaryKey, ObjectHistoryTracker):
    """Stores record of exported or imported model entities."""

    class TaskStatuses(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS"
        SUCCESS = "SUCCESS"
        FAIL = "FAIL"

    last_modified_at = None
    created_by = models.ForeignKey(
        "accounts.AccountUser",
        verbose_name=_("primary user"),
        on_delete=models.CASCADE,
    )
    owner_id = models.UUIDField(
        verbose_name=_("created by"),
        # editable=False,
        help_text=_(
            "the Id of the ClustR account user who created this data exchange."
        ),
    )
    completed_at = models.DateTimeField(
        verbose_name=_("completion date"), null=True, blank=True
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        choices=TaskStatuses.choices,
        # editable=False,
    )
    content_type = models.ForeignKey(
        verbose_name=_("content type"),
        to=ContentType,
        on_delete=models.CASCADE,
        # editable=False,
        help_text=_("django model content type to be exported or imported."),
    )
    notify_on_success = models.BooleanField(
        verbose_name=_("notify on success"),
        default=False,
        help_text=_("notify the user after an import or export succeeds"),
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        default_permissions = []

    def save(self, *args, **kwargs):
        self.full_clean()
        should_notify = self._should_send_on_success_notification()
        super().save(*args, **kwargs)
        if should_notify:
            self._send_on_success_notification()

    def _send_on_success_notification(self):
        self._build_on_success_email()
        # TODO: Send email Notification

    def _build_on_success_email(self) -> TransactionalEmail:
        # subject = self._SUCCESS_NOTIFICATION_EMAIL_SUBJECT
        # template_name = self._SUCCESS_NOTIFICATION_TEMPLATE_NAME
        # context = Context(dict_={"task": self})
        # Note: We want to give admins and the relevant users with permissions full
        # visibility of what's going on in the account so all relevant users with permissions
        # relevant to this model and above should get the notification. a function that returns these
        # list of users would be helpful here
        ...

    def __str__(self) -> str:
        return cast(str, self.content_type.model)

    def _should_send_on_success_notification(self) -> bool:
        if not self.notify_on_success:
            return False
        if self.status != BaseTask.TaskStatuses.SUCCESS:
            return False
        original_task = type(self).objects.filter(pk=self.pk).first()
        return original_task and original_task.status != BaseTask.TaskStatuses.SUCCESS


class ExportTask(BaseTask):
    external_file_id = models.UUIDField(
        verbose_name=_("external file id"),
        null=True,
        # editable=False,
        help_text=_(
            "the external file id (AWS/Cloudinary) if the file is stored in external."
        ),
    )

    sql_query = models.TextField(
        verbose_name=_("sql query"),
        # editable=False,
        help_text=_(
            "the SQL query used to extract the exported data. Maybe from queryset.query"
        ),
    )

    class Meta(BaseTask.Meta):
        verbose_name = _("export task")
        verbose_name_plural = _("export tasks")

    def delete(self, using=None, keep_parents=False):
        # NOTE: remove file from Third-party platform since we'll use either use AWS or Cloudinary
        super().delete(using=None, keep_parents=False)

    def get_absolute_url(self):
        return reverse(
            "export-detail", kwargs={"version": settings.API_VERSION, "pk": self.pk}
        )

    @classmethod
    def create_in_progress_task(
        cls,
        owner_id: UUID,
        queryset: QuerySet,
        notify_on_success: bool,
        created_by: Optional[UUID] = None,
    ):
        content_type = ContentType.objects.get_for_model(queryset.model)
        return cls.objects.create(
            owner_id=owner_id,
            created_by=created_by,
            status=cls.TaskStatuses.IN_PROGRESS,
            content_type=content_type,
            sql_query=str(queryset.query),
            notify_on_success=notify_on_success,
        )

    def mark_as_successful(self, external_file_id: Optional[UUID] = None):
        self.external_file_id = external_file_id
        self.status = BaseTask.TaskStatuses.SUCCESS
        self.completed_at = timezone.now()
        try:
            # Users have options to delete the import or export. The task may be deleted while it is still in
            # progress. In this case, when the task finishes and tries to update status, an error will occur.
            # Here, we just suppress the error.
            self.save()
        except ObjectDoesNotExist:
            pass

    def mark_as_failed(self):
        self.status = BaseTask.TaskStatuses.FAIL
        try:
            # Uses have option to delete tasks. The task may have been deleted before this API
            # is called asynchronously
            self.save(update_fields=["status", "last_modified_at"])
        except ObjectDoesNotExist:
            pass


class ImportTask(BaseTask):
    imported_object_ids = ArrayField(
        models.CharField(max_length=40),
        verbose_name=_("Import IDs"),
        default=list,
        blank=True,
        help_text=_("The IDs of the imported objects"),
    )
    errors = models.JSONField(
        verbose_name=_("errors"),
        default=list,
        blank=True,
        help_text=_(
            "A list of dictionary of serialized RowError objects encountered during the import"
        ),
    )
    total_skipped = models.PositiveIntegerField(
        verbose_name=_("total skipped"),
        default=0,
        help_text=_("The total number of rows that were fully skipped due to errors"),
    )

    class Meta(BaseTask.Meta):
        verbose_name = _("import task")
        verbose_name_plural = _("import tasks")

    def get_absolute_url(self):
        return reverse(
            "import-detail", kwargs={"version": settings.API_VERSION, "pk": self.pk}
        )

    @classmethod
    def create_in_progress_task(
        cls,
        created_by: "AccountUser",
        content_type: ContentType,
        notify_on_success: bool,
        owner_id: Optional[UUID] = None,
    ):
        return cls.objects.create(
            owner_id=owner_id,
            created_by=created_by,
            status=cls.TaskStatuses.IN_PROGRESS,
            content_type=content_type,
            notify_on_success=notify_on_success,
        )

    def mark_as_successful(
        self, imported_object_ids: list[str], errors: list[dict], total_skipped: int
    ):
        self.status = BaseTask.TaskStatuses.SUCCESS
        self.imported_object_ids = imported_object_ids
        self.errors = errors
        self.total_skipped = total_skipped
        self.completed_at = timezone.now()
        try:
            self.save()
        except ObjectDoesNotExist:
            pass

    def mark_as_failed(self, errors: list[dict]):
        self.status = BaseTask.TaskStatuses.FAIL
        self.errors = errors
        try:
            # Users have option to delete tasks. The task may have been deleted before this API
            # is called asynchronously
            self.save(update_fields=["status", "errors", "last_modified_at"])
        except ObjectDoesNotExist:
            pass
