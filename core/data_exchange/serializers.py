from pathlib import Path
from typing import Collection, Optional, Type, cast

from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from rest_framework import serializers
from rest_framework.fields import Field

from core.data_exchange.includes.types import MAX_IMPORT_FILE_SIZE, FileFormats
from core.data_exchange.models import ExportTask, ImportTask

base_fields = [
    "id",
    "owner_id",
    "status",
    "created_at",
    "last_modified_at",
]


class ExportTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTask
        fields = base_fields + ["external_file_id", "notify_on_success"]


class ImportTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportTask
        fields = base_fields + ["imported_object_ids", "errors", "total_skipped"]


class NotifyOnSuccessSerializer(serializers.Serializer):
    notify_on_success = serializers.BooleanField(required=False, default=False)


class DataExchangeFileFormatSerializer(serializers.Serializer):
    allowed_formats = [FileFormats.CSV, FileFormats.XLSX]

    format = serializers.ChoiceField(
        [(e.value, e.name) for e in allowed_formats],
        default=FileFormats.CSV.value,
        required=False,
    )


class BaseExportOptionsSerializer(
    NotifyOnSuccessSerializer, DataExchangeFileFormatSerializer
):
    ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )


class BaseImportedDataSerializer(serializers.Serializer):
    """
    Base serializer for validating request data for imported files.
    Subclasses should extend and add any other custom data fields required from the user client to successfully
    import a particular model.
    """

    # List of attributes that can be imported for this content type. Subclasses should override this with
    # a collection of attributes that can be imported from a file. For example, a subclass to import Contact model
    # can list attributes ["first_name", "last_name"]
    IMPORTABLE_ATTRIBUTES: Collection[str] = []

    column_mapping = serializers.JSONField(
        help_text=(
            "A mapping of column header name or index to the Imported Django model entity attribute name."
            "For example, a file can have a header 'The customers first name'. The correct mapping would be"
            "{ 'The customers first name': 'first_name' }"
        ),
    )
    format = serializers.ChoiceField(
        choices=FileFormats.choices,
        required=False,
        help_text=(
            "Optional format of the file. If not provided, the format will be guessed. This will only work "
            "if the file name has a suffix"
        ),
    )
    has_headers = serializers.BooleanField(help_text="Does the file have headers?")
    file = serializers.FileField(
        help_text=(
            "The file to be imported. This file will not be saved permanently. "
            "It will only be used to read the import data after which it should be discarded."
        )
    )
    should_upsert = serializers.BooleanField(
        default=True,
        help_text="Should we use the imported data to update data that already exist in your account?",
    )

    def validate_file(self, value: File) -> Optional[File]:
        if value.size > MAX_IMPORT_FILE_SIZE:
            raise serializers.ValidationError(
                "Maximum allowed file size of 100 MB exceeded."
            )
        return value

    def validate_column_mapping(self, value: dict) -> dict:
        if not value:
            raise serializers.ValidationError("At least one field is required")

        invalid = []
        for attribute in value.values():
            if attribute not in self.IMPORTABLE_ATTRIBUTES:
                invalid.append(attribute)
        if invalid:
            raise serializers.ValidationError(
                f"One or more unknown attribute(s) found - {', '.join(invalid)}"
            )
        return value

    def _allow_attribute_for_import(self, attribute: str) -> bool:
        """
        Subclasses can override this method to check if an imported attribute should be allowed
        """
        return True

    def validate(self, attrs: dict) -> Optional[dict]:
        super().validate(attrs)
        file: File = attrs.get("file")
        if not file:
            return attrs
        suffix = Path(file.name).suffix.removeprefix(".")
        if not suffix and attrs.get("format") is None:
            raise serializers.ValidationError(
                {
                    "file": (
                        "file name suffix is required for file names with no suffix, rename the file to include "
                        "file format. For example 'my customers.csv' instead of 'my customers' or provide "
                        "the 'format' parameter in the request body"
                    )
                }
            )

        allowed_suffixes = [suffix.name.lower() for suffix in list(FileFormats)]
        if suffix and suffix.lower() not in allowed_suffixes:
            raise serializers.ValidationError(
                {
                    "file": "Unsupported file format. Only '.csv', '.xls', and '.xlsx' files are supported."
                }
            )
        return attrs


class BaseExportListSerializer(serializers.ListSerializer):
    def to_representation(self, data: list) -> list[dict]:
        result = []
        for item in data:
            result.extend(self.child.to_representation(item))
        return result


class DynamicFieldsSerializer(serializers.Serializer):
    """
    The base class for data import and export serializer implementations
    """

    data = serializers.ListSerializer(
        child=serializers.DictField(),
        help_text="The default imported field. Used only for import",
    )

    def __init__(self, *args, **kwargs):
        """
        extra_fields - Any extra module fields/attributes to be included in the base exported fields
        import_data - Serialized data from an instance
          of core.data_exchange.serializers.BaseImportedDataSerializer that holds preferences
          and options for data import
        """
        extra_fields = kwargs.pop("extra_fields", ())
        import_data = kwargs.pop("import_data", {})
        super().__init__(*args, **kwargs)
        self.extra_fields = extra_fields
        self.import_data = import_data

    @classmethod
    def get_content_type(cls) -> ContentType:
        """*Only useful for imports. Return the content type object being imported"""
        raise NotImplementedError


class BaseExportSerializer(DynamicFieldsSerializer):
    extra_fields = []
    export_options = {}

    class Meta:
        list_serializer_class = BaseExportListSerializer


def build_runtime_serializer(fields: dict[str, Field]) -> Type[serializers.Serializer]:
    new_class = type("RuntimeSerializer", (serializers.Serializer,), fields)
    return cast(Type[serializers.Serializer], new_class)
