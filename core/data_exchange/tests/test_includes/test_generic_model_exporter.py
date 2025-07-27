from unittest.mock import MagicMock

from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from accounts.tests.utils import TestUsers, create_fake_request
from core.data_exchange.includes.generic_model_exporter import (
    GenericModelExporter,
)
from core.data_exchange.includes.types import FileFormats
from core.data_exchange.models import ExportTask


class GenericModelExporterTestCases(TestUsers, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.request = create_fake_request(owner_id=cls.owner1["owner_id"], data={})
        cls.request.data = {}
        serializer_class = MagicMock()
        serializer_class.is_valid.return_value = True
        serializer_class.data = {
            "ids": [],
            "notify_on_success": True,
            "extra_fields": [],
            "format": FileFormats.CSV,
        }
        cls.options_serializer_class = MagicMock(return_value=serializer_class)
        cls.export_serializer_class = Serializer
        cls.queryset = ExportTask.objects.all()
        cls.queryset.model = ExportTask
        cls.generic_model_exporter = GenericModelExporter(
            request=cls.request,
            base_queryset=cls.queryset,
            export_serializer_class=cls.export_serializer_class,
            options_serializer_class=cls.options_serializer_class,
        )

    def test_get_response(self):
        response = self.generic_model_exporter.get_response()
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")

    def test_get_export_queryset(self):
        queryset = self.generic_model_exporter._get_export_queryset(None)
        self.assertEqual(queryset, self.queryset)

    def test_create_export_task(self):
        task = self.generic_model_exporter._create_export_task(self.queryset, False)
        self.assertEqual(str(task.owner_id), self.owner1["owner_id"])
        self.assertEqual(str(task.created_by), self.owner1["user_id"])
        self.assertFalse(task.notify_on_success)

    def test_is_async_export(self):
        self.generic_model_exporter._task = (
            self.generic_model_exporter._create_export_task(self.queryset, True)
        )
        self.assertTrue(self.generic_model_exporter._is_async)
