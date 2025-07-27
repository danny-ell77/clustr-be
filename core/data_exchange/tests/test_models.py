from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from core.data_exchange.models import ExportTask, ImportTask
from core.data_exchange.tests.utils import (
    create_test_export_task,
    create_test_import_task,
)


class ExportTaskModelTestCase(TestCase):
    def setUp(self) -> None:
        self.content_type = ContentType.objects.get_for_model(ExportTask)
        self.valid_data, self.export_task = create_test_export_task(
            owner_id=self.owner1["owner_id"],
            created_by=self.owner1["owner_id"],
            content_type=self.content_type,
        )

    def test_model_is_created(self):
        self.assertIsInstance(self.export_task, ExportTask)

    def test_model_fields(self):
        self.assertEqual(str(self.export_task.owner_id), self.valid_data["owner_id"])
        self.assertEqual(
            str(self.export_task.created_by), self.valid_data["created_by"]
        )
        self.assertEqual(self.export_task.status, self.valid_data["status"])
        self.assertEqual(self.export_task.content_type, self.valid_data["content_type"])
        self.assertEqual(self.export_task.sql_query, self.valid_data["sql_query"])
        self.assertEqual(
            self.export_task.notify_on_success, self.valid_data["notify_on_success"]
        )

    def test_get_absolute_url(self):
        self.assertURLEqual(
            self.export_task.get_absolute_url(),
            f"/api/{settings.API_VERSION}/data-exchange/exports/{self.export_task.id}/",
        )

    def test_string_representation(self):
        self.assertEqual(str(self.export_task), self.export_task.content_type.model)

    def test_verbose_names(self):
        verbose_name = self.export_task._meta.verbose_name
        verbose_name_plural = self.export_task._meta.verbose_name_plural
        self.assertEqual(verbose_name, "export task")
        self.assertEqual(verbose_name_plural, "export tasks")

    def test_mark_as_failed(self):
        self.assertEqual(self.export_task.status, ExportTask.TaskStatuses.IN_PROGRESS)
        self.export_task.mark_as_failed()
        self.export_task.refresh_from_db()
        self.assertEqual(self.export_task.status, ExportTask.TaskStatuses.FAIL)

    def test_create_in_progress_task(self):
        export_task = ExportTask.create_in_progress_task(
            owner_id=self.owner1["owner_id"],
            queryset=ExportTask.objects.all(),
            notify_on_success=True,
            created_by=self.owner1["user_id"],
        )
        self.assertTrue(export_task)
        self.assertEqual(export_task.status, ExportTask.TaskStatuses.IN_PROGRESS)


class ImportTaskModelTestCase(TestCase):
    def setUp(self) -> None:
        self.export_task_content_type = ContentType.objects.get_for_model(ExportTask)
        self.valid_data, self.import_task = create_test_import_task(
            owner_id=self.owner1["owner_id"],
            created_by=self.owner1["owner_id"],
            content_type=self.export_task_content_type,
        )

    def test_model_is_created(self):
        self.assertTrue(self.import_task)

    def test_model_fields(self):
        self.assertEqual(
            f"{self.import_task.created_by}", self.valid_data["created_by"]
        )
        self.assertEqual(f"{self.import_task.owner_id}", self.valid_data["owner_id"])
        self.assertEqual(self.import_task.status, self.valid_data["status"])
        self.assertEqual(self.import_task.content_type, self.valid_data["content_type"])
        self.assertEqual(
            self.import_task.notify_on_success, self.valid_data["notify_on_success"]
        )

    def test_get_absolute_url(self):
        self.assertURLEqual(
            self.import_task.get_absolute_url(),
            f"/api/{settings.API_VERSION}/data-exchange/imports/{self.import_task.id}/",
        )

    def test_string_representation(self):
        self.assertEqual(str(self.import_task), self.import_task.content_type.model)

    def test_verbose_names(self):
        verbose_name = self.import_task._meta.verbose_name
        verbose_name_plural = self.import_task._meta.verbose_name_plural
        self.assertEqual(verbose_name, "import task")
        self.assertEqual(verbose_name_plural, "import tasks")

    def test_mark_as_failed(self):
        self.assertEqual(self.import_task.status, ImportTask.TaskStatuses.IN_PROGRESS)
        self.import_task.mark_as_failed(errors=[])
        self.import_task.refresh_from_db()
        self.assertEqual(self.import_task.status, ImportTask.TaskStatuses.FAIL)

    def test_create_in_progress_task(self):
        import_task = ImportTask.create_in_progress_task(
            owner_id=self.owner1["owner_id"],
            content_type=self.export_task_content_type,
            notify_on_success=True,
            created_by=self.owner1["user_id"],
        )
        self.assertTrue(import_task)
        self.assertEqual(import_task.status, ImportTask.TaskStatuses.IN_PROGRESS)
