import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.core.validators import RegexValidator
from django.utils.timezone import make_aware
from rest_framework import serializers

from core.data_exchange.exceptions import RowError
from core.data_exchange.includes.types import BackwardReturnType
from core.data_exchange.serializers import build_runtime_serializer


def validate_email_address(
    field_name: str, value: Any, row_number: int, error_title: str, **kwargs
) -> BackwardReturnType:
    kwargs.setdefault("max_length", 100)
    max_length = kwargs["max_length"]
    serializer_class = build_runtime_serializer(
        {
            field_name: serializers.EmailField(
                **kwargs,
                error_messages={
                    "invalid": f"{field_name}: Invalid email address",
                    "blank": f"{field_name}: Must not be blank",
                    "max_length": f"{field_name}: Must not be more than {max_length} characters",
                },
            )
        }
    )
    serializer = serializer_class(data={field_name: value})
    return _process_serializer(serializer, field_name, row_number, error_title)


def validate_phone_number(
    field_name: str,
    value: Any,
    row_number: int,
    default_dialing_code: str,
    error_title: str,
    **kwargs,
) -> BackwardReturnType:
    if not str(value).startswith("+") and not default_dialing_code:
        error = RowError(
            row_number=row_number,
            description=(
                f"{field_name}: This attribute must be provided in your request if your phone number does "
                f"not include country dialing code"
            ),
            title=default_dialing_code,
        )
        return [error], None
    if value and not str(value).startswith("+"):
        value = f"{default_dialing_code}{value}"

    # Removes any non-digit characters in the phone number except for the first '+' character.
    value = "+" + re.sub(r"\D", "", value)
    kwargs.setdefault("max_length", 16)
    kwargs.setdefault("min_length", 3)
    max_length = kwargs["max_length"]
    min_length = kwargs["min_length"]
    serializer_class = build_runtime_serializer(
        {
            field_name: serializers.CharField(
                **kwargs,
                validators=[
                    RegexValidator(
                        "^\+[1-9]\d{1,14}$",
                        message=f"{field_name}: Invalid phone number",
                    )
                ],
                error_messages={
                    "invalid": f"{field_name}: Invalid phone number",
                    "blank": f"{field_name}: Must not be blank",
                    "max_length": f"{field_name}: Must be between {min_length} and {max_length} characters",
                    "min_length": f"{field_name}: Must be between {min_length} and {max_length} characters",
                },
            )
        }
    )
    serializer = serializer_class(data={field_name: value})
    return _process_serializer(serializer, field_name, row_number, error_title)


def validate_decimal_field(
    field_name: str, value: Any, row_number: int, error_title: str, **kwargs
) -> BackwardReturnType:
    kwargs.setdefault("max_digits", 11)
    kwargs.setdefault("decimal_places", 2)
    kwargs.setdefault("min_value", Decimal("0"))
    max_digits = kwargs["max_digits"]
    decimal_places = kwargs["decimal_places"]
    max_value = kwargs.get("max_value")
    min_value = kwargs["min_value"]

    min_value_error_msg = f"{field_name}: Must be a positive number or zero"
    if min_value < Decimal("0"):
        min_value_error_msg = (
            f"{field_name}: Must be greater than or equal to {min_value}"
        )

    value = value or None
    serializer_class = build_runtime_serializer(
        {
            field_name: serializers.DecimalField(
                **kwargs,
                error_messages={
                    "null": f"{field_name}: Invalid or missing value",
                    "invalid": f"{field_name}: Invalid value",
                    "blank": f"{field_name}: Must not be blank",
                    "min_value": min_value_error_msg,
                    "max_value": f"{field_name}: Must be less than or equal to {max_value}",
                    "max_digits": f"{field_name}: Must be no more than {max_digits} digits in total",
                    "max_decimal_places": f"{field_name}: Must have {decimal_places} decimal places or less",
                    "max_whole_digits": f"{field_name}: Must not have more than {max_digits - decimal_places} digits before the decimal point",
                },
            )
        }
    )
    serializer = serializer_class(data={field_name: value})
    return _process_serializer(serializer, field_name, row_number, error_title)


def _process_serializer(
    serializer: serializers.Serializer,
    field_name: str,
    row_number: int,
    error_title: str,
) -> BackwardReturnType:
    if serializer.is_valid():
        return [], serializer.validated_data[field_name]
    errors = []
    for error_info in serializer.errors[field_name]:
        error = RowError(
            row_number=row_number,
            description=str(error_info),
            title=error_title,
        )
        errors.append(error)
    return errors, None


def validate_generic_name(
    field_name: str, value: Any, row_number: int, error_title: str, **kwargs
) -> BackwardReturnType:
    kwargs.setdefault("max_length", 100)
    max_length = kwargs["max_length"]
    min_length = kwargs.get("min_length")
    serializer_class = build_runtime_serializer(
        {
            field_name: serializers.CharField(
                **kwargs,
                error_messages={
                    "invalid": f"{field_name}: Invalid value",
                    "blank": f"{field_name}: Must not be blank",
                    "max_length": f"{field_name}: Must not be more than {max_length} characters",
                    "min_length": f"{field_name}: Must not be less than {min_length} characters",
                },
            )
        }
    )
    serializer = serializer_class(data={field_name: value})
    return _process_serializer(serializer, field_name, row_number, error_title)


def parse_integer(
    field_name: str, value: Any, row_number: int, error_title: str, **kwargs
) -> BackwardReturnType:
    max_value = kwargs.get("max_value")
    kwargs.setdefault("min_value", 0)
    min_value = kwargs["min_value"]

    min_value_error_msg = f"{field_name}: Must be a positive number or zero"
    if min_value < 0:
        min_value_error_msg = (
            f"{field_name}: Must be greater than or equal to {min_value}"
        )

    serializer_class = build_runtime_serializer(
        {
            field_name: serializers.IntegerField(
                **kwargs,
                error_messages={
                    "null": f"{field_name}: Invalid or missing value",
                    "invalid": f"{field_name}: Invalid number",
                    "blank": f"{field_name}: Must not be blank",
                    "max_value": f"{field_name}: Must be less than or equal to {max_value}",
                    "min_value": min_value_error_msg,
                },
            )
        }
    )
    serializer = serializer_class(data={field_name: value})
    return _process_serializer(serializer, field_name, row_number, error_title)


def parse_date_from_string(
    field_name: str,
    value: str,
    row_number: int,
    error_title: str,
    **kwargs,
) -> BackwardReturnType:
    try:
        parsed_date = datetime.strptime(value, "%m-%d-%Y").date()
        return [], parsed_date
    except ValueError:
        try:
            parsed_date = datetime.strptime(value, "%B %d, %Y").date()
            return [], parsed_date
        except ValueError:
            error = RowError(
                row_number=row_number,
                description=(
                    f"{field_name}: Invalid date format. Use MM-DD-YYYY or MMMM DD, YYYY; "
                    f"e.g. 04-25-2022 or April 25th, 2022"
                ),
                title=error_title,
            )
            return [error], None


def parse_datetime_from_string(
    field_name: str,
    value: str,
    row_number: int,
    error_title: str,
    **kwargs,
) -> BackwardReturnType:
    try:
        # A problem - the accounts' timezone is used. This may not be what the user wants.
        # We should probably support ISO date format with timezone support.
        parsed_datetime = datetime.strptime(value, "%m-%d-%Y %H:%M")
        return [], make_aware(parsed_datetime)
    except ValueError:
        try:
            parsed_datetime = datetime.strptime(value, "%B %d, %Y at %I:%M %p")
            return [], make_aware(parsed_datetime)
        except ValueError:
            error = RowError(
                row_number=row_number,
                description=(
                    f"{field_name}: Invalid datetime format. Use MM-DD-YYYY HH:MM or MMMM DD, YYYY at HH:MM AM/PM; "
                    f"e.g. 04-25-2022 22:23 or April 25th, 2022 at 11:23 PM"
                ),
                title=error_title,
            )
            return [error], None


def parse_boolean(
    field_name: str,
    value: str,
    row_number: int,
    error_title: str,
    **kwargs,
):
    if value.upper() not in ["TRUE", "FALSE"]:
        error = RowError(
            row_number=row_number,
            description=f"{field_name}: Invalid value. Must be TRUE or FALSE",
            title=error_title,
        )
        return [error], None
    valid = value.upper() == "TRUE"
    return [], valid
