import mimetypes
import string
from io import BytesIO
from pathlib import Path
from typing import Type, Optional
from uuid import UUID

import pandas as pd
from django.conf import settings
from django.db.models import Model, QuerySet
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from rest_framework.serializers import Serializer

from core.data_exchange.exceptions import DataExportException
from core.data_exchange.includes.types import (
    FileFormats,
    StorageLocations,
    ExportOutput,
)
from core.data_exchange.includes.utils import encode_output_buffer

TEMP_DIR = settings.TEMP_DIR
TEMP_DIR.mkdir(parents=True, exist_ok=True)


class RecordExporter:
    """
    Generic data exporter for exporting model queryset results using a serializer with support for CSV and XLSX files.
    Output can be stored locally or to an external service.
    """

    def __init__(
        self,
        model_class: Type[Model],
        queryset_dict: dict,
        serializer_class: Type[Serializer],
        serializer_extra_fields: Optional[list[str]] = None,
        output_format: FileFormats = FileFormats.CSV,
        storage_location: StorageLocations = StorageLocations.EXTERNAL,
        owner_id: UUID = None,
        always_on_external=True,
    ):
        """
        Parameters
        :param model_class: The Django model class that will be exported
        :param queryset_dict: The original queryset dictionary derived from Queryset.__dict__, which is used to
          rebuild the original queryset with cached select_related and prefetch_related attributes
        :param serializer_class: A Serializer subclass that will receive the queryset for serialization as
          a list (with parameter many=True). The serializer is responsible to transforming the queryset to a list
          of data that will then be written to the output CSV or XLSX file
        :param serializer_extra_fields: Optional list of extra field names that will be included in the export in
          addition to the base field names for the exported model
        :param output_format: The format of the exported field.
          Enum - core.data_exchange.includes.types.FileFormats
        :param storage_location: The target location of the exported result file.
          Enum - core.data_exchange.includes.types.StorageLocations
        :param owner_id: The account's owner id
        :param always_on_external: Force all exports to be store on external in addition to any other target storage
          location specified
        """
        if (
            always_on_external or storage_location == StorageLocations.EXTERNAL
        ) and not owner_id:
            raise DataExportException(
                _("owner_id is required to store files on external")
            )
        self.model_class = model_class
        self.queryset_dict = queryset_dict
        self.serializer_class = serializer_class
        self.serializer_extra_fields: list[str] = serializer_extra_fields
        self.output_format = output_format
        self.storage_location = storage_location
        self.owner_id = owner_id
        self.always_on_external = always_on_external
        self._output_rows: list[dict] = []
        self._buffer: BytesIO = BytesIO()
        self._now = timezone.now()
        allowed_chars = string.ascii_lowercase + string.digits
        self._random_file_name_jitter = get_random_string(
            length=8, allowed_chars=allowed_chars
        )

    @cached_property
    def _file_name(self) -> str:
        """
        Computes a somewhat unique filename.
        Example output: 'Product_2020-05-10_23-04-45_kpewe37f.csv'
        """
        model_class_name = self.model_class.__name__.title()
        date_time = self._now.strftime("%Y-%m-%d_%H-%M-%S")  # E.g. 2020-05-10_23-04-45
        suffix = ".csv" if self.output_format == FileFormats.CSV else ".xlsx"
        return f"{model_class_name}_{date_time}_{self._random_file_name_jitter}{suffix}"

    @property
    def _file_mimetype(self) -> Optional[str]:
        return mimetypes.guess_type(self._file_name)[0]

    def export(self) -> ExportOutput:
        self._write_rows()
        self._write_spreadsheet_to_buffer()
        external_file_id = None
        common = {
            "file_name": self._file_name,
            "mime_type": self._file_mimetype,
        }
        if self.always_on_external:
            external_file_id = self._save_to_external_service()
        if self.storage_location == StorageLocations.MEMORY_FILE:
            return ExportOutput(
                file=encode_output_buffer(self._buffer),
                external_file_id=external_file_id,
                **common,
            )
        if self.storage_location == StorageLocations.DISK_FILE:
            return ExportOutput(
                file=self._save_to_local_disk(),
                external_file_id=external_file_id,
                **common,
            )
        if self.storage_location == StorageLocations.EXTERNAL:
            external_file_id = self._save_to_external_service()
            return ExportOutput(
                file=external_file_id, external_file_id=external_file_id, **common
            )

    def _write_rows(self):
        queryset = self._rebuild_queryset()
        serializer = self.serializer_class(
            queryset,
            many=True,
            extra_fields=self.serializer_extra_fields,
            context={"owner_id": self.owner_id},
        )
        self._output_rows.extend(serializer.data)

    def _rebuild_queryset(self) -> QuerySet:
        queryset = self.model_class.objects.all()
        queryset.__dict__ = self.queryset_dict
        return queryset

    def _write_spreadsheet_to_buffer(self):
        data_frame = pd.DataFrame.from_records(data=self._output_rows)
        if self.output_format == FileFormats.CSV:
            data_frame.to_csv(
                path_or_buf=self._buffer, index=False, float_format="%.2f"
            )
        elif self.output_format == FileFormats.XLSX:
            data_frame.to_excel(
                excel_writer=self._buffer,
                sheet_name="Sheet1",
                index=False,
                float_format="%.2f",
            )

    def _save_to_local_disk(self) -> Path:
        # This is located in the celery process's file system, not the application's file system.
        path = TEMP_DIR / self._file_name
        with path.open("ab") as writer:
            writer.write(self._buffer.getvalue())
        return path

    def _save_to_external_service(self) -> Optional[UUID]: ...
