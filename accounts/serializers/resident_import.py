from typing import Any, Collection

from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import transaction
from django.template import Context
from rest_framework import serializers

from accounts.models import AccountUser, UserVerification
from accounts.serializers.users import AccountSerializer
from core.common.email_sender import AccountEmailSender, NotificationTypes
from core.data_exchange.exceptions import RowError
from core.data_exchange.includes.imported_attribute_validators import (
    validate_email_address,
    validate_generic_name,
    validate_phone_number,
)
from core.data_exchange.includes.types import (
    AttributeResolver,
    BackwardReturnType,
    ImportResult,
)
from core.data_exchange.serializers import (
    BaseImportedDataSerializer,
    DynamicFieldsSerializer,
)

IMPORT_ROW_NUMBER = int

CORE_ATTRIBUTES = ["name", "email_address", "phone_number"]


class ResidentImportedDataSerializer(BaseImportedDataSerializer):
    IMPORTABLE_ATTRIBUTES = CORE_ATTRIBUTES

    default_dialing_code = serializers.CharField(
        max_length=5,
        min_length=2,
        validators=[RegexValidator(r"^\+\d{1,4}$")],
        default="",
        help_text=(
            "The default dialing code of imported phone number without dialing code prefix. If you are "
            "importing a column with phone numbers, we require the phone numbers to be in E.164 format "
            "and have prefix"
        ),
    )


class ResidentImportExportSerializer(DynamicFieldsSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cluster_id = self.context["cluster_id"]
        self._owner_id = self.context["owner_id"]
        self._cluster_staff_id = self.context["cluster_staff_id"]
        self._global_errors: list[RowError] = []
        self._validated_row_data: dict[IMPORT_ROW_NUMBER, dict] = {}
        self._new_resident_accounts: dict[str, AccountUser] = {}
        self._existing_residents: dict[str, AccountUser] = {}
        self._seen_email_addresses = set()
        self._error_offset = 2 if self.import_data.get("has_headers") else 1

    @classmethod
    def get_content_type(cls) -> ContentType:
        return ContentType.objects.get_for_model(AccountUser)

    def to_internal_value(self, data: dict[str, list[dict]]) -> Collection[AccountUser]:
        data: list[dict[str, Any]] = super().to_internal_value(data)["data"]
        for row_number, row_data in enumerate(data, self._error_offset):
            validation_errors, _ = self._validate_row_data(row_data, row_number)
            if validation_errors:
                self._global_errors.extend(validation_errors)

            duplicate_errors, _ = self._check_for_duplicates(row_data, row_number)
            if duplicate_errors:
                self._global_errors.extend(duplicate_errors)

        if self._global_errors:
            self._global_errors.sort(key=lambda error: error.row_number)
            raise serializers.ValidationError(
                {"errors": [error.to_dict() for error in self._global_errors]}
            )

        self.load_existing_residents(data)

        for row_number, row_data in enumerate(data, self._error_offset):
            if row_data["email_address"] in self._existing_residents:
                # self._existing_residents should be linked to the Cluster
                if self.import_data["should_upsert"]:
                    self._update_old_resident(row_data, row_number)
            else:
                self._initialize_new_resident(row_data, row_number)

        return list(self._new_resident_accounts.values())

    def _validate_row_data(self, row_data: dict, row_number: int) -> BackwardReturnType:
        """
        For each of the imported rows, runs the backward resolver to resolve and validate the imported value for
        each attribute.
        """
        valid_data = {}
        validation_errors: list[RowError] = []
        for attribute, resolver in self._attribute_resolvers.items():
            errors = []
            result = None
            backward_resolver = resolver["backward_resolver"]
            if backward_resolver is not None:
                errors, result = backward_resolver(row_data, row_number)
            if errors:
                validation_errors.extend(errors)
            else:
                valid_data[attribute] = result

        if validation_errors:
            return validation_errors, None
        self._validated_row_data[row_number] = valid_data
        return [], None

    def _check_for_duplicates(
        self, row_data: dict, row_number: int
    ) -> BackwardReturnType:
        name = row_data["name"]
        if name in self._seen_email_addresses:
            error = RowError(
                row_number=row_number,
                description="name: Duplicate resident email address found. "
                "Please make sure all email addresses are unique",
                title=row_data.get("name"),
            )
            return [error], None
        self._seen_email_addresses.add(name)
        return [], None

    def load_existing_residents(self, data: list[dict[str, Any]]):
        email_addresses = {row_data["email_address"] for row_data in data}

        self._existing_residents = AccountUser.objects.filter(
            owner_id=self._owner_id, email_address__in=email_addresses
        ).in_bulk(field_name="email_address")

    def _update_old_resident(self, row_data: dict, row_number: int):
        resident = self._existing_residents[row_data["email_address"]]
        valid_data = self._validated_row_data[row_number]
        resident.phone_number = valid_data["phone_number"]
        resident.name = valid_data["name"]

    def _initialize_new_resident(self, row_data: dict, row_number: int):
        valid_data = self._validated_row_data[row_number]
        resident = AccountUser(
            owner_id=self._owner_id,
            cluster_id=self._cluster_id,
            name=valid_data["name"],
            phone_number=valid_data["phone_number"],
            email_address=valid_data["email_address"],
        )
        resident.prepare_for_import()
        self._new_resident_accounts[resident.email_address] = resident

    @property
    def _attribute_resolvers(self) -> dict[str, AttributeResolver]:
        """
        Mapping of attributes to export or import and their respective serialization and deserialization functions
        """
        return {
            "name": {
                "name": "name",
                "forward_resolver": None,
                "backward_resolver": self._name_backward_resolver,
            },
            "email_address": {
                "name": "email_address",
                "forward_resolver": None,
                "backward_resolver": self._email_address_backward_resolver,
            },
            "phone_number": {
                "name": "phone_number",
                "forward_resolver": None,
                "backward_resolver": self._phone_number_backward_resolver,
            },
        }

    def _name_backward_resolver(self, row_data: dict, row_number: int):
        return validate_generic_name(
            field_name="name",
            value=row_data["name"],
            row_number=row_number,
            error_title=row_data["name"],
            max_length=150,
            min_length=1,
        )

    def _email_address_backward_resolver(self, row_data: dict, row_number: int):
        return validate_email_address(
            field_name="email_address",
            value=row_data["email_address"],
            row_number=row_number,
            error_title=row_data["email_address"],
        )

    def _phone_number_backward_resolver(self, row_data: dict, row_number: int):
        return validate_phone_number(
            field_name="phone_number",
            value=row_data["phone_number"],
            row_number=row_number,
            error_title=row_data["phone_number"],
            default_dialing_code=self.import_data["default_dialing_code"],
        )

    def save(self):
        imported_residents = self._persist_residents()
        serializer = AccountSerializer(imported_residents, many=True)
        object_ids = [str(resident.pk) for resident in imported_residents]
        self._global_errors.sort(key=lambda error: error.row_number)

        summary = ImportResult(
            errors=self._global_errors,
            data=serializer.data,
            object_ids=object_ids,
            total_skipped=0,
        )
        return summary

    @transaction.atomic()
    def _persist_residents(self) -> list[AccountUser]:
        def _on_commit():
            # Add other post import actions
            self._send_verification_tokens()

        transaction.on_commit(_on_commit)

        residents_to_update = list(self._existing_residents.values())
        AccountUser.objects.bulk_update(residents_to_update, fields=CORE_ATTRIBUTES)
        new_resident_accounts = AccountUser.objects.bulk_create(
            self._new_resident_accounts.values(), ignore_conflicts=True
        )
        self._send_verification_tokens()

        if self.import_data["should_upsert"]:
            return new_resident_accounts + residents_to_update
        return new_resident_accounts

    def _send_verification_tokens(self):
        for new_residents in self._get_residents():
            recipient_data = {}
            verification_tokens = []
            for resident in new_residents:
                verification_tokens.append(
                    UserVerification(
                        requested_by=resident,
                        notification_type=NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET,
                    )
                )
            tokens = UserVerification.objects.bulk_create(
                verification_tokens,
                batch_size=1_000,
                ignore_conflicts=True,
            )
            for token in tokens:
                resident = token.requested_by
                recipient_data[resident.email_address] = Context(
                    dict_={"name": resident.name, "token": token.otp}
                )
            AccountEmailSender(
                recipient_data.keys(),
                NotificationTypes.ONBOARDING_OTP_PASSWORD_RESET,
            ).send_to_many(recipient_data)

    def _get_residents(self):
        yield AccountUser.objects.filter(
            email_address__in=self._new_resident_accounts.keys(),
        ).iterator(chunk_size=1_000)
