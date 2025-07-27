import re
from unittest import mock
from uuid import uuid4

from django.conf import settings
from django.test import TestCase

from accounts.tests.utils import TestUsers
from core.data_exchange.includes.record_exporter import RecordExporter
from core.data_exchange.models import ExportTask
from core.data_exchange.serializers import BaseExportSerializer


class RecordExporterTestCases(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        bigdrive_patcher = mock.patch(
            "core.data_exchange.includes.record_exporter.RecordExporter._save_to_bigdrive"
        )
        bigdrive_mock = bigdrive_patcher.start()
        bigdrive_mock.return_value = str(uuid4())

        cls.queryset = ExportTask.objects.all()
        cls.record_exporter = RecordExporter(
            model_class=ExportTask,
            queryset_dict=cls.queryset.__dict__,
            serializer_class=BaseExportSerializer,
            owner_id=cls.owner1["owner_id"],
            always_on_bigdrive=True,
        )

    def test_export(self):
        export_output = self.record_exporter.export()
        self.assertEqual(export_output.file_name, self.record_exporter._file_name)
        self.assertEqual(export_output.mime_type, self.record_exporter._file_mimetype)

    def test_write_rows(self):
        self.assertFalse(self.record_exporter._output_rows)
        self.record_exporter._write_rows()
        self.assertListEqual(self.record_exporter._output_rows, [])

    def test_rebuild_queryset(self):
        query = self.record_exporter._rebuild_queryset()
        self.assertListEqual(list(query), list(self.queryset))

    def test_write_spreadsheet_to_buffer(self):
        self.assertTrue(self.record_exporter._buffer.getbuffer().nbytes == 0)
        self.record_exporter._write_spreadsheet_to_buffer()
        self.assertTrue(self.record_exporter._buffer.getbuffer().nbytes > 0)

    def test_save_to_local_disk(self):
        self.record_exporter._write_spreadsheet_to_buffer()
        path = self.record_exporter._save_to_local_disk()
        self.assertEqual(settings.TEMP_DIR / self.record_exporter._file_name, path)

    def test_file_name(self):
        self.assertTrue(
            bool(
                re.match(
                    r"^"
                    + ExportTask.__name__.title()
                    + "_"
                    + self.record_exporter._now.strftime("%Y-%m-%d_%H-%M-%S")
                    + "_[a-z0-9]{8}(.csv|.xlsx)",
                    self.record_exporter._file_name,
                )
            )
        )

    def test_file_mimetype(self):
        self.assertEqual(self.record_exporter._file_mimetype, "text/csv")
