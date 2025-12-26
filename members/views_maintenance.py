"""
Maintenance views for estate residents.
"""

import logging
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from core.common.models import (
    MaintenanceLog,
    MaintenanceType,
    MaintenancePriority,
    PropertyType,
)
from core.common.serializers.maintenance import (
    MaintenanceLogSerializer,
    MaintenanceLogCreateSerializer,
    MaintenanceAttachmentSerializer,
    MaintenanceCommentSerializer,
    MaintenanceCommentCreateSerializer,
    MaintenanceHistorySerializer,
    MaintenanceLogUpdateSerializer,
)
from core.common.includes import maintenance
from core.common.responses import success_response, error_response
from core.common.decorators import audit_viewset
from members.filters import MemberMaintenanceLogFilter, MemberMaintenanceHistoryFilter

logger = logging.getLogger("clustr")


class MaintenancePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


@audit_viewset(resource_type="member_maintenance_log")
class MemberMaintenanceLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing maintenance logs for members.
    Provides CRUD operations and custom actions for attachments, comments, history, and status.
    """

    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberMaintenanceLogFilter
    pagination_class = MaintenancePagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MaintenanceLog.objects.none()

        cluster= getattr(self.request, "cluster_context", None)
        return self.queryset.filter(
            cluster=cluster, requested_by=self.request.user
        ).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return MaintenanceLogCreateSerializer
        elif self.action == "update" or self.action == "partial_update":
            return MaintenanceLogUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        cluster= getattr(self.request, "cluster_context", None)
        maintenance_log = maintenance.create_log(
            cluster=cluster, requested_by=self.request.user, **serializer.validated_data
        )
        serializer.instance = maintenance_log

    @action(
        detail=True, methods=["get"], url_path="attachments", url_name="attachments"
    )
    def attachments(self, request, pk=None):
        """
        Get attachments for a maintenance request.
        """
        maintenance_log = self.get_object()
        attachments = maintenance_log.attachments.all().order_by("created_at")
        serializer = MaintenanceAttachmentSerializer(attachments, many=True)
        return success_response(
            data=serializer.data,
            message="Maintenance attachments retrieved successfully",
        )

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="upload-attachment",
        url_name="upload_attachment",
    )
    def upload_attachment(self, request, pk=None):
        """
        Upload an attachment for a maintenance request.
        """
        maintenance_log = self.get_object()

        file_obj = request.FILES.get("file")
        if not file_obj:
            return error_response(
                message="File is required", status_code=status.HTTP_400_BAD_REQUEST
            )

        attachment_type = request.data.get("attachment_type", "OTHER")
        description = request.data.get("description", "")

        try:
            attachment = maintenance.upload_attachment(
                maintenance_log=maintenance_log,
                file_obj=file_obj,
                attachment_type=attachment_type,
                uploaded_by=request.user,
                description=description,
            )
            serializer = MaintenanceAttachmentSerializer(attachment)
            return success_response(
                data=serializer.data,
                message="Attachment uploaded successfully",
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error uploading maintenance attachment: {str(e)}")
            return error_response(
                message="Failed to upload attachment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True, methods=["get", "post"], url_path="comments", url_name="comments"
    )
    def comments(self, request, pk=None):
        """
        Get comments for a maintenance request or add a new comment.
        """
        maintenance_log = self.get_object()

        if request.method == "GET":
            comments = maintenance_log.comments.filter(
                is_internal=False, parent__isnull=True
            ).order_by("created_at")
            serializer = MaintenanceCommentSerializer(comments, many=True)
            return success_response(
                data=serializer.data,
                message="Maintenance comments retrieved successfully",
            )
        elif request.method == "POST":
            serializer = MaintenanceCommentCreateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    maintenance_log=maintenance_log,
                    author=request.user,
                    cluster=request.cluster_context,
                    created_by=request.user.id,
                    is_internal=False,
                )
                return success_response(
                    data=serializer.data,
                    message="Comment added successfully",
                    status_code=status.HTTP_201_CREATED,
                )
            return error_response(
                message="Invalid data provided",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="history", url_name="history")
    def history(self, request):
        """
        Get maintenance history for properties associated with the current user.
        """
        cluster= getattr(self.request, "cluster_context", None)
        queryset = MaintenanceLog.objects.filter(
            cluster=cluster, requested_by=self.request.user
        ).order_by("-created_at")

        # Apply history filter
        filterset = MemberMaintenanceHistoryFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            return error_response(
                message="Invalid filter parameters",
                errors=filterset.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        queryset = filterset.qs

        limit = request.query_params.get("limit", 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        queryset = queryset[:limit]

        serializer = MaintenanceHistorySerializer(queryset, many=True)
        return success_response(
            data=serializer.data, message="Maintenance history retrieved successfully"
        )

    @action(detail=True, methods=["get"], url_path="status", url_name="status")
    def status(self, request, pk=None):
        """
        Get the current status of a maintenance request.
        """
        instance = self.get_object()
        status_data = {
            "maintenance_number": instance.maintenance_number,
            "title": instance.title,
            "status": instance.status,
            "status_display": instance.get_status_display(),
            "priority": instance.priority,
            "priority_display": instance.get_priority_display(),
            "scheduled_date": instance.scheduled_date,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at,
            "performed_by": (
                {
                    "id": instance.performed_by.id,
                    "name": instance.performed_by.name,
                }
                if instance.performed_by
                else None
            ),
            "is_overdue": instance.is_overdue,
            "is_due_soon": instance.is_due_soon,
            "time_remaining": instance.time_remaining,
            "created_at": instance.created_at,
            "last_modified_at": instance.last_modified_at,
        }
        return success_response(
            data=status_data, message="Maintenance status retrieved successfully"
        )


def maintenance_choices(request):
    """
    Get choices for maintenance-related fields (for residents).
    """
    try:
        choices = {
            "maintenance_types": [
                {"value": choice[0], "label": choice[1]}
                for choice in MaintenanceType.choices
            ],
            "maintenance_priorities": [
                {"value": choice[0], "label": choice[1]}
                for choice in MaintenancePriority.choices
            ],
            "property_types": [
                {"value": choice[0], "label": choice[1]}
                for choice in PropertyType.choices
            ],
            "attachment_types": [
                {"value": "BEFORE", "label": "Before Photo"},
                {"value": "DURING", "label": "During Work"},
                {"value": "AFTER", "label": "After Photo"},
                {"value": "RECEIPT", "label": "Receipt"},
                {"value": "OTHER", "label": "Other"},
            ],
        }

        return success_response(
            data=choices, message="Maintenance choices retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error retrieving maintenance choices: {str(e)}")
        return error_response(
            message="Failed to retrieve maintenance choices",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
