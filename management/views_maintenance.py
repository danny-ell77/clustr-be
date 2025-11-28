"""
Maintenance management views for estate administrators.
"""

import logging
from datetime import datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from core.common.models import (
    MaintenanceLog,
    MaintenanceSchedule,
    MaintenanceType,
    MaintenanceStatus,
    MaintenancePriority,
    PropertyType,
)
from core.common.serializers.maintenance import (
    MaintenanceLogSerializer,
    MaintenanceLogUpdateSerializer,
    MaintenanceScheduleSerializer,
    MaintenanceAttachmentSerializer,
    MaintenanceSummarySerializer,
    MaintenanceOptimizationSerializer,
    MaintenanceHistorySerializer,
    MaintenanceLogCreateSerializer,
    MaintenanceScheduleCreateSerializer,
)
from core.common.includes import maintenance
from core.common.responses import success_response, error_response
from core.common.error_codes import CommonAPIErrorCodes
from core.common.decorators import audit_viewset
from accounts.models import AccountUser
from accounts.permissions import IsClusterStaffOrAdmin
from management.filters import MaintenanceLogFilter, MaintenanceScheduleFilter


logger = logging.getLogger("clustr")


class MaintenancePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@audit_viewset(resource_type="maintenance_log")
class MaintenanceLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing maintenance logs.
    Provides CRUD operations and custom actions for assignment, attachment, history, analytics, and optimizations.
    """

    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [IsClusterStaffOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MaintenanceLogFilter
    pagination_class = MaintenancePagination

    def get_queryset(self):
        cluster= getattr(self.request, "cluster_context", None)
        return self.queryset.filter(cluster=cluster).order_by("-created_at")

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

    def perform_update(self, serializer):
        serializer.instance.last_modified_by = self.request.user.id
        serializer.save()

    @action(detail=True, methods=["post"])
    def assign_maintenance(self, request, pk=None):
        """
        Assign maintenance to a staff member.
        """
        maintenance_log = self.get_object()

        try:
            assigned_to_id = request.data.get("assigned_to")
            if not assigned_to_id:
                return error_response(
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message="assigned_to is required",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            try:
                assigned_to = AccountUser.objects.get(id=assigned_to_id)
            except AccountUser.DoesNotExist:
                return error_response(
                    error_code=CommonAPIErrorCodes.RESOURCE_NOT_FOUND,
                    message="Assigned user not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            maintenance.assign_log(
                maintenance_log=maintenance_log,
                assigned_to=assigned_to,
                assigned_by=request.user,
            )

            serializer = self.get_serializer(maintenance_log)
            return success_response(
                data=serializer.data, message="Maintenance assigned successfully"
            )

        except Exception as e:
            logger.error(f"Error assigning maintenance: {str(e)}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to assign maintenance",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        """
        Upload an attachment for a maintenance log.
        """
        maintenance_log = self.get_object()

        try:
            file_obj = request.FILES.get("file")
            if not file_obj:
                return error_response(
                    error_code=CommonAPIErrorCodes.VALIDATION_ERROR,
                    message="File is required", 
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            attachment_type = request.data.get("attachment_type", "OTHER")
            description = request.data.get("description", "")

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
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to upload attachment",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def history(self, request):
        """
        Get maintenance history with optional filtering.
        """
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return error_response(
                "Cluster context not found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            property_location = request.GET.get("property_location")
            equipment_name = request.GET.get("equipment_name")
            property_type = request.GET.get("property_type")
            limit = request.GET.get("limit")

            if limit:
                try:
                    limit = int(limit)
                except ValueError:
                    limit = None

            history = maintenance.get_history(
                cluster=cluster,
                property_location=property_location,
                equipment_name=equipment_name,
                property_type=property_type,
                limit=limit,
            )

            serializer = MaintenanceHistorySerializer(history, many=True)
            return success_response(
                data=serializer.data,
                message="Maintenance history retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving maintenance history: {str(e)}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve maintenance history",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """
        Get maintenance analytics and statistics.
        """
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return error_response(
                error_code=CommonAPIErrorCodes.CLUSTER_NOT_FOUND,
                message="Cluster context not found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = request.GET.get("start_date")
            end_date = request.GET.get("end_date")

            start_date_parsed = None
            end_date_parsed = None

            if start_date:
                try:
                    start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if end_date:
                try:
                    end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    pass

            analytics = maintenance.get_analytics(
                cluster=cluster, start_date=start_date_parsed, end_date=end_date_parsed
            )

            serializer = MaintenanceSummarySerializer(analytics)
            return success_response(
                data=serializer.data,
                message="Maintenance analytics retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving maintenance analytics: {str(e)}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve maintenance analytics",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def optimizations(self, request):
        """
        Get maintenance optimization suggestions.
        """
        cluster = getattr(request, 'cluster_context', None)
        if not cluster:
            return error_response(
                error_code=CommonAPIErrorCodes.CLUSTER_NOT_FOUND,
                message="Cluster context not found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            suggestions = maintenance.suggest_optimizations(cluster)

            serializer = MaintenanceOptimizationSerializer(suggestions, many=True)
            return success_response(
                data=serializer.data,
                message="Maintenance optimization suggestions retrieved successfully",
            )

        except Exception as e:
            logger.error(f"Error retrieving maintenance optimizations: {str(e)}")
            return error_response(
                error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
                message="Failed to retrieve maintenance optimizations",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@audit_viewset(resource_type="maintenance_schedule")
class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing maintenance schedules.
    Provides CRUD operations.
    """

    queryset = MaintenanceSchedule.objects.all()
    serializer_class = MaintenanceScheduleSerializer
    permission_classes = [IsClusterStaffOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MaintenanceScheduleFilter

    def get_queryset(self):
        cluster= getattr(self.request, "cluster_context", None)
        return self.queryset.filter(cluster=cluster).order_by("next_due_date")

    def get_serializer_class(self):
        if self.action == "create":
            return MaintenanceScheduleCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        cluster= getattr(self.request, "cluster_context", None)
        schedule = maintenance.create_schedule(
            cluster=cluster, created_by=self.request.user, **serializer.validated_data
        )
        serializer.instance = schedule


def maintenance_categories(request):
    """
    Get maintenance categories by property and equipment.
    """
    cluster = getattr(request, 'cluster_context', None)
    if not cluster:
        return error_response(
                error_code=CommonAPIErrorCodes.CLUSTER_NOT_FOUND,
                message="Cluster context not found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    try:
        property_type = request.GET.get("property_type")
        maintenance_type = request.GET.get("maintenance_type")

        categories = maintenance.get_by_category(
            cluster=cluster,
            property_type=property_type,
            maintenance_type=maintenance_type,
        )

        return success_response(
            data=categories, message="Maintenance categories retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error retrieving maintenance categories: {str(e)}")
        return error_response(
            error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to retrieve maintenance categories",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def maintenance_choices(request):
    """
    Get choices for maintenance-related fields.
    """
    try:
        choices = {
            "maintenance_types": [
                {"value": choice[0], "label": choice[1]}
                for choice in MaintenanceType.choices
            ],
            "maintenance_statuses": [
                {"value": choice[0], "label": choice[1]}
                for choice in MaintenanceStatus.choices
            ],
            "maintenance_priorities": [
                {"value": choice[0], "label": choice[1]}
                for choice in MaintenancePriority.choices
            ],
            "property_types": [
                {"value": choice[0], "label": choice[1]}
                for choice in PropertyType.choices
            ],
        }

        return success_response(
            data=choices, message="Maintenance choices retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error retrieving maintenance choices: {str(e)}")
        return error_response(
            error_code=CommonAPIErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to retrieve maintenance choices",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
