import mimetypes
from typing import Any, Mapping, Optional, Type

import pandas as pd
from django.core.files import File
from django.utils.translation import gettext as _

from core.data_exchange.exceptions import (
    UnknownFileFormatException,
    DataImportException,
)
from core.data_exchange.includes.types import FileFormats, ImportResult
from core.data_exchange.serializers import DynamicFieldsSerializer


class RecordImporter:
    """
    Generic data importer for importing data from CSV, XLS and XLSX. Clients must provide a serializer to handle
    the list of values imported from the file.
    """

    def __init__(
        self,
        import_data: dict[str, Any],
        import_serializer_class: Type[DynamicFieldsSerializer],
        serializer_context: Optional[dict] = None,
    ):
        """
        Parameters
        :param import_data: Mapping describing how the file should be imported. The dictionary data is derived
          from a serializer subclass of core.data_exchange.serializers.BaseImportedDataSerializer
        :param import_serializer_class: A serializer class where the imported data will be loaded, if the file
          contains an invalid rows
        :param serializer_context: Any extra context data that should be passed to the serializer
        """
        self.import_data = import_data
        self.import_serializer_class = import_serializer_class
        self.serializer_context = serializer_context or {}
        self._file_format: FileFormats = self.import_data.get("format")
        self._file: File = self.import_data["file"]
        self._has_headers: bool = self.import_data["has_headers"]
        self._column_mapping: dict[str, Any] = self.import_data["column_mapping"]

    def import_(self) -> ImportResult:
        """
        Instantiates the import serializer class with the imported file data and returns the return type
        of the Serializer's 'save' method
        :raises:
            UnknownFileFormatException: If the file's type is not specified, and it cannot be determined
            using the file name
            DataImportException: If no data is found in the imported file
        """
        data = self._dataframe_to_dict()
        if not data:
            raise DataImportException(
                "The imported file does not contain any valid data"
            )

        serializer = self.import_serializer_class(
            data={"data": data},
            import_data=self.import_data,
            context=self.serializer_context or {},
        )

        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        # Django's temporary file is implemented using Python's tempfile.NamedTemporaryFile class. So, before we
        # return, we need to close the file, so it's deleted from the file system immediately.
        self._file.close()

        return result

    def _dataframe_to_dict(self) -> list[Mapping[str, Any]]:
        dataframe = self._file_to_dataframe()
        if self._has_headers:
            dataframe.rename(columns=self._column_mapping, inplace=True)
        else:
            # Pandas require that column header indexes be ints. Here, we need to cast the string keys to ints
            # e.g. { "1" : "firstname" } -> { 1: "firstname" }
            columns = {
                int(column): self._column_mapping[column]
                for column in self._column_mapping
            }
            dataframe.rename(columns=columns, inplace=True)

        return dataframe.to_dict(orient="records")

    def _file_to_dataframe(self) -> pd.DataFrame:
        if self._has_headers:
            columns = list(self._column_mapping.keys())
        else:
            columns = list(map(int, list(self._column_mapping.keys())))

        file_format = self._get_file_format()
        try:
            if file_format == FileFormats.CSV:
                data = pd.read_csv(
                    self._file,
                    usecols=columns,
                    header="infer" if self._has_headers else None,
                    dtype=str,
                )
            else:
                data = pd.read_excel(
                    self._file,
                    usecols=columns,
                    header=0 if self._has_headers else None,
                    dtype=str,
                )
        except ValueError as error:
            raise DataImportException(error)
        data.fillna(value="", inplace=True)
        return data

    def _get_file_format(self) -> Optional[FileFormats]:
        """
        Returns the file format of the import file if specified or the file format is guessed using the file name
        """
        if self._file_format is not None:
            return self._file_format

        probable_format = mimetypes.guess_type(self._file.name)[0]
        if probable_format == "text/csv":
            return FileFormats.CSV

        if (
            probable_format
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            return FileFormats.XLSX

        if probable_format == "application/vnd.ms-excel":
            return FileFormats.XLS

        raise UnknownFileFormatException(
            _(
                "Unable to determine file type. Supported file types are CSV, XLS and XLSX"
            )
        )
