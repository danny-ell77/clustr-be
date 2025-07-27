from typing import Optional


class DataExchangeException(Exception):
    ...


class DataExportException(DataExchangeException):
    ...


class DataImportException(DataExchangeException):
    ...


class UnknownFileFormatException(DataExchangeException):
    ...


class RowError(DataExchangeException):
    """
    Error object returned while parsing and validating rows of imported data.
    """

    def __init__(self, row_number: int, description, title: Optional[str] = None):
        """
        Parameters
        :param row_number: The row number where the error occurred
        :param description: Description of the error. This should include detailed information and solution to fix
          the error
        :param title: Extra error headline. For example, product name or order external ID.
        """
        self.row_number = row_number
        self.description = description
        self.title = title

    def __str__(self):
        return f"Error on row: {self.row_number}. {self.description}"

    def to_dict(self) -> dict:
        return self.__dict__
