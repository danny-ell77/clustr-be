from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import AccountUser, UserVerification
from accounts.serializers import (
    ResidentImportedDataSerializer,
    ResidentImportExportSerializer,
)
from accounts.tests.test_serializers import fixtures
from accounts.tests.utils import (
    TestUsers,
    create_fake_request,
    create_mock_cluster_admin,
)
from core.data_exchange.includes.types import FileFormats, ImportResult


def create_test_file(file_path: Path, file_name: str) -> SimpleUploadedFile:
    with file_path.open("rb") as f:
        file_data = f.read()
        return SimpleUploadedFile(file_name, file_data)


IMPORT_DATA = {
    "file": create_test_file(fixtures.EXCEL_WITH_HEADERS, "file.csv"),
    "format": FileFormats.XLSX,
    "column_mapping": {
        "name": "name",
        "email address": "email_address",
        "phone number": "phone_number",
    },
    "should_upsert": False,
    "has_headers": True,
    "default_dialing_code": "+234",
}


class ImportDataSerializerTestCase(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.valid_data = IMPORT_DATA
        cls.invalid_data = {
            "file": "asdkajsbd",
            "format": "invalid",
            "column_mapping": {"invalid": "invalid"},
            "should_upsert": "invalid",
            "has_headers": "invalid",
            "default_dialing_code": "invalid",
        }
        cls.serializer_class = ResidentImportedDataSerializer

    def test_valid_data(self):
        serializer = self.serializer_class(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_data(self):
        for key, value in self.invalid_data.items():
            with self.subTest(key, valid=self.valid_data[key], invalid=value):
                data = self.valid_data.copy()
                data[key] = value
                serializer = self.serializer_class(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn(key, serializer.errors)


class ClusterMembersImportSerializerTestCase(TestCase):
    # TODO: No test for failures! pls revisit.
    @classmethod
    def setUp(cls):
        cls.cluster_admin = create_mock_cluster_admin()
        cls.valid_data = [
            {
                "name": "Daniel Olah",
                "email_address": "mock@example.com",
                "phone_number": "09056705721",
            }
        ]
        cls.mock_notification_manager_send = patch(
            "core.notifications.manager.NotificationManager.send"
        ).start()
        request = create_fake_request(owner=cls.cluster_admin)
        cls.serializer = ResidentImportExportSerializer(
            data={"data": cls.valid_data},
            import_data=IMPORT_DATA,
            context={
                "cluster_id": request.user.cluster_id,
                "owner_id": request.user.get_owner().id,
                "cluster_staff_id": request.user.id,
            },
        )

    def test_valid_data(self):
        self.assertTrue(self.serializer.is_valid())
        self.serializer.save()
        self.assertIsInstance(self.serializer.validated_data, list)
        self.assertTrue(self.serializer.validated_data)
        self.assertDictEqual(self.serializer.errors, {})

    def test_number_of_created_instances__on__valid_data(self):
        self.serializer.is_valid()
        self.serializer.save()
        self.assertEqual(self._created_users.count(), len(self.valid_data))

    def test_email_verification_initiated__on__valid_data(self):
        self.serializer.is_valid()
        self.serializer.save()
        self.assertEqual(UserVerification.objects.count(), len(self.valid_data))
        self.mock_notification_manager_send.assert_called()

    def test_import_result__on__valid_data(self):
        self.serializer.is_valid()
        import_summary = self.serializer.save()
        self.assertIsInstance(import_summary, ImportResult)
        self.assertEqual(len(import_summary.data), len(self.valid_data))
        self.assertListEqual(import_summary.errors, [])

    def test_data_fields__on__valid_data(self):
        self.serializer.is_valid()
        self.serializer.save()
        users_dict = {user.email_address: user for user in self._created_users}

        for user_data in self.valid_data:
            user = users_dict.get(user_data["email_address"])
            for key, value in user_data.items():
                value = self._transform_value(key, value)
                with self.subTest(key, expected=value):
                    self.assertEqual(getattr(user, key), value)

    @property
    def _created_users(self):
        return AccountUser.objects.filter(
            email_address__in=[data["email_address"] for data in self.valid_data],
        )

    def _transform_value(self, key, value):
        # Very ugly but the other alternative is to test manually
        if key == "phone_number":
            value = IMPORT_DATA["default_dialing_code"] + value
        return value
