from collections import OrderedDict
from pathlib import Path
from typing import Optional, Mapping, Any

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.data_exchange.includes.record_importer import RecordImporter
from core.data_exchange.includes.types import FileFormats, ImportResult
from core.data_exchange.models import ImportTask
from core.data_exchange.serializers import DynamicFieldsSerializer
from core.data_exchange.tests.test_includes import fixtures


class MockModelImportSerializer(DynamicFieldsSerializer):
    @classmethod
    def get_content_type(cls) -> ContentType:
        return ContentType.objects.get_for_model(ImportTask)

    def save(self, **kwargs) -> ImportResult:
        # Performs the object creation and returns an import result
        return ImportResult(
            errors=[], data=[self.validated_data], object_ids=[], total_skipped=0
        )


class RecordImporterTestCases(SimpleTestCase):
    def _get_importer_instance(
        self,
        file_path: Path,
        file_name: str,
        column_mapping: Mapping[str, Any],
        has_headers: bool,
        format: Optional[FileFormats] = None,
    ) -> RecordImporter:
        with file_path.open("rb") as f:
            file_data = f.read()
        file = SimpleUploadedFile(file_name, file_data)
        import_data = {
            "column_mapping": column_mapping,
            "format": format,
            "has_headers": has_headers,
            "file": file,
        }
        return RecordImporter(
            import_data=import_data,
            import_serializer_class=MockModelImportSerializer,
            serializer_context=None,
        )

    def test_can_import_csv_file_with_headers(self):
        column_mapping = {"customer name": "name", "email": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.CSV_WITH_HEADERS,
            file_name="file.csv",
            column_mapping=column_mapping,
            has_headers=True,
            format=FileFormats.CSV,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )

    def test_can_import_csv_file_without_headers(self):
        column_mapping = {"0": "name", "1": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.CSV_WITHOUT_HEADERS,
            file_name="file.csv",
            column_mapping=column_mapping,
            has_headers=False,
            format=FileFormats.CSV,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )

    def test_can_import_excel_file_with_headers(self):
        column_mapping = {"name": "name", "email": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.EXCEL_WITH_HEADERS,
            file_name="file.xlsx",
            column_mapping=column_mapping,
            has_headers=True,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )

    def test_can_import_excel_file_without_headers(self):
        column_mapping = {"0": "name", "1": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.EXCEL_WITHOUT_HEADERS,
            file_name="file.xlsx",
            column_mapping=column_mapping,
            has_headers=False,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )

    def test_can_import_excel_file_legacy_with_headers(self):
        column_mapping = {"name": "name", "email": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.EXCEL_LEGACY_WITH_HEADERS,
            file_name="file.xls",
            column_mapping=column_mapping,
            has_headers=True,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )

    def test_can_import_excel_file_legacy_without_headers(self):
        column_mapping = {"0": "name", "1": "email"}
        record_importer = self._get_importer_instance(
            file_path=fixtures.EXCEL_LEGACY_WITHOUT_HEADERS,
            file_name="file.xls",
            column_mapping=column_mapping,
            has_headers=False,
        )
        imports = record_importer.import_()
        self.assertIsInstance(imports, ImportResult)
        self.assertListEqual(
            [
                OrderedDict(
                    [("data", [{"name": "John Doe", "email": "jd@example.com"}])]
                )
            ],
            imports.data,
        )
