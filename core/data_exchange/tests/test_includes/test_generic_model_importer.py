from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status

from accounts.tests.utils import TestUsers, create_fake_request
from core.data_exchange.includes.generic_model_importer import (
    GenericModelImporter,
)
from core.data_exchange.includes.types import FileFormats
from core.data_exchange.models import ImportTask
from core.data_exchange.serializers import BaseImportedDataSerializer
from core.data_exchange.tests.test_includes import fixtures
from core.data_exchange.tests.test_includes.test_record_importer import (
    MockModelImportSerializer,
)


def create_test_file(file_path: Path, file_name: str) -> SimpleUploadedFile:
    with file_path.open("rb") as f:
        file_data = f.read()
        return SimpleUploadedFile(file_name, file_data)


class GenericModelImporterTestCases(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.request = create_fake_request(owner=cls.owner, data={})
        cls.request.data = {
            "column_mapping": {
                "customer name": "name",
                "email": "email",
            },
            "format": FileFormats.CSV,
            "has_headers": True,
            "file": create_test_file(fixtures.CSV_WITH_HEADERS, "file.csv"),
        }
        cls.async_importer = GenericModelImporter(
            request=cls.request,
            import_serializer_class=MockModelImportSerializer,
            import_data_serializer_class=BaseImportedDataSerializer,
            is_async=True,
        )
        cls.sync_importer = GenericModelImporter(
            request=cls.request,
            import_serializer_class=MockModelImportSerializer,
            import_data_serializer_class=BaseImportedDataSerializer,
            is_async=False,
        )

    def test_get_response_for_async_import(self):
        queryset = ImportTask.objects.filter(status=ImportTask.TaskStatuses.IN_PROGRESS)
        self.assertFalse(queryset.exists())
        response = self.async_importer.get_response()
        self.assertTrue(queryset.exists())
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(ImportTask.objects.filter(pk=response.data["id"]).exists())

    def test_get_response_for_sync_import(self):
        response = self.sync_importer.get_response()
        self.assertFalse(ImportTask.objects.exists())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            response.data, [{"data": [{"name": "John Doe", "email": "jd@example.com"}]}]
        )
