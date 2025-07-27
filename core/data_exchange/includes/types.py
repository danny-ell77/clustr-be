from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, NamedTuple, Optional, TypedDict, TypeVar
from uuid import UUID

from django.db import models

from core.data_exchange.exceptions import RowError

MAX_IMPORT_FILE_SIZE = 1024 * 1024  # 100 MB max imported file size


class FileFormats(models.TextChoices):
    CSV = "CSV"
    XLSX = "XLSX"
    XLS = "XLS"  # Not supported for export


class StorageLocations(str, Enum):
    """
    The location exported file will be stored.
    DiskFile - Stores the file in the local disk. May be fine for small files. Avoid this for any file more than a few
        KBs, and you should have a mechanism to delete the file when done.
    MemoryFile = Store the file in the process memory. Best offload the task to an async worker, so it doesn't eat into
    the main process's memory.
    """

    DISK_FILE = "DISK_FILE"
    MEMORY_FILE = "MEMORY_FILE"
    EXTERNAL = "EXTERNAL"


# Return type for the exported file.
# BytesIO - Returned for in memory file storage
# Path - Returned for in disk file
# UUID - File id returned for file stored in BigDrive
ExportedFile = TypeVar("ExportedFile", Path, str)


class ExportOutput(NamedTuple):
    file: ExportedFile
    file_name: str
    mime_type: str
    external_file_id: UUID


@dataclass(frozen=True, order=False)
class ImportResult:
    """
    The return type for data import serializers.
    An instance of this class is returned when an import is complete. It contains the information on the result
    of the import, such as the errors that occurred while performing the import or the result of a successful import

    Attributes
    errors:
        A list of errors that occurred while importing. if errors is non-empty,
        any value in the data and object_ids attributes are invalid and should
        be ignored
    data:
        A list of the imported instances in their serialized form
    object_ids:
        A list of identifiers of the imported object instances. For example, a list of object primary keys
    total_skipped:
        The total number of rows that were fully skipped due to errors
    """

    errors: list[RowError]
    data: list[dict]
    object_ids: list[str]
    total_skipped: int

    def serialized_errors(self) -> list[dict]:
        return [error.to_dict() for error in self.errors]


AttributeValue = TypeVar("AttributeValue", str, int, float, list)

BackwardReturnType = tuple[list[RowError], Optional]


class AttributeResolver(TypedDict):
    """
    Attribute resolves are responsible for serializer and deserializing models to exportable format.
    name:- This is the rendered named of the model attribute. It may be different from the name of the field in
      model. For example, the 'media' field is Product model rendered as 'media_urls'

    forward_resolver:- Is a callables responsible for serializing the object field to a primitive value.

    backward_resolver:- Is a callable responsible for deserializing primitive value to a valid object of the
      target model field. Validations should be performed to ensure correct values so that no Validation
      errors are raised while creating or updating the model.
    """

    name: str
    forward_resolver: Optional[Callable[..., AttributeValue]]
    backward_resolver: Optional[Callable[..., BackwardReturnType]]


class ImportedRowData(NamedTuple):
    row_number: int
    row_data: dict
