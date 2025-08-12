from typing import cast

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q, QuerySet
from django.http import FileResponse, HttpResponseBase
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend


from accounts.models import AccountUser, UserVerification, VerifyMode, VerifyReason
from accounts.filters import AccountUserFilter
from accounts.permissions import CanManageAccountUsers, IsClusterAdmin
from accounts.serializers import (
    AccountSerializer,
    PasswordChangeSerializer,
    PermissionField,
    ResidentImportedDataSerializer,
    ResidentImportExportSerializer,
    StaffAccountSerializer,
    SubuserAccountSerializer,
    EmailVerificationSerializer,
)
from accounts.utils import change_password
from core.common.email_sender import AccountEmailSender, NotificationTypes
from core.common.exceptions import InvalidDataException
from core.common.responses import duplicate_entity_response
from core.common.includes import build_runtime_serializer
from core.data_exchange.includes.generic_model_importer import GenericModelImporter
from core.common.decorators import audit_viewset
from core.common.error_utils import exception_to_response_mapper


@audit_viewset(resource_type='user')
class UserViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AccountUserFilter

    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated & CanManageAccountUsers]

    def get_queryset(self) -> QuerySet:
        user = cast(AccountUser, self.request.user)
        queryset = (
            AccountUser.objects.filter(
                Q(pk=user.pk) | Q(owner=user.get_owner()) | Q(clusters__in=user.clusters.all())
            )
            .select_related("cluster")
            .prefetch_related("groups")
        )
        search_param = self.request.query_params.get("search")
        if search_param:
            queryset = queryset.filter(
                Q(email_address__icontains=search_param) |
                Q(first_name__icontains=search_param) |
                Q(last_name__icontains=search_param)
            )
        return queryset

    def update(self, request: Request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return duplicate_entity_response(
                detail=_("A user with the email already exists")
            )

    @action(
        detail=False,
        methods=["GET"],
        url_path="from-auth",
        url_name="from_auth",
    )
    def get_account_information_from_auth(
        self, request: Request, *args, **kwargs
    ) -> Response:
        """
        Endpoint to get the account information by using the data from the auth user instead
        of requiring an ID. This is required for frontend as at the time it requests to load
        the account information, it doesn't yet know the account id.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=EmailVerificationSerializer(),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="{'detail': 'Verification email sent successfully'}"
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="{'detail': 'User with this email does not exist'}"
            ),
        },
        operation_description="Initialize email verification",
    )
    @action(
        methods=["POST"],
        detail=False,
        url_name="email_verification",
        url_path="email-verification",
        permission_classes=[AllowAny],
    )
    def initialize_email_verification(
        self, request: Request, *args, **kwargs
    ) -> Response:
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["verify_mode"]

        user = AccountUser.objects.filter(
            email_address__iexact=serializer.validated_data["email_address"]
        ).first()
        if not user:
            return Response(
                {"detail": "User with this email does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_verified:
            return Response(
                {"detail": "User is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mode = VerifyMode(value)
        except ValueError:
            raise InvalidDataException(detail="Invalid verification mode")
        UserVerification.for_mode(
            mode, user=user, reason=VerifyReason.ONBOARDING
        ).send_mail()
        return Response(
            {"detail": "Verification email sent successfully"},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="{'detail': 'Successfully changes user permissions'}"
            ),
        },
    )
    @action(
        methods=["POST"],
        detail=True,
        url_name="change_permissions",
        url_path="change-permissions",
        permission_classes=[CanManageAccountUsers],
    )
    def change_permissions(self, request: Request, *args, **kwargs) -> Response:
        """
        This API accepts a list of strings defined as codenames for various permission classes
        here in the backend. This endpoint changes the permissions completely
        """
        serializer_class = build_runtime_serializer(
            {"permissions": PermissionField(many=True)}
        )
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_object()
        user.user_permissions.set(serializer.validated_data["permissions"])
        return Response(
            {"detail": "Successfully changed user permissions"},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        request_body=PasswordChangeSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="{'detail': 'Password changed successfully'}"
            ),
            status.HTTP_205_RESET_CONTENT: openapi.Response(
                description="{'detail': 'Password changed successfully'}"
            ),
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="change-password",
        url_name="change_password",
    )
    def change_password(self, request: Request, *args, **kwargs) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        force_logout: bool = data["force_logout"]
        user = cast(AccountUser, request.user)
        change_password(
            user=user,
            new_password=data["new_password"],
            current_password=data["current_password"],
            force_logout=force_logout,
        )
        AccountEmailSender(
            recipients=[user.email_address],
            email_type=NotificationTypes.PASSWORD_CHANGED,
        ).send()
        status_code = (
            status.HTTP_205_RESET_CONTENT if force_logout else status.HTTP_200_OK
        )
        return Response({"detail": "Password changed successfully"}, status=status_code)

    @swagger_auto_schema(
        request_body=StaffAccountSerializer,
        responses={status.HTTP_200_OK: StaffAccountSerializer()},
    )
    @action(
        methods=["POST"],
        detail=False,
        url_name="add_staff",
        url_path="add-staff",
        permission_classes=[IsClusterAdmin],
    )
    def add_staff(self, request: Request, *args, **kwargs) -> Response:
        """
        If the admin edits the permissions for a pre-defined role, the permission for that role
        defined in the context of that admin is updated on-click.
        Then the id is submitted with the new user information
        """
        try:
            serializer = StaffAccountSerializer(
                data=request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except IntegrityError:
            return duplicate_entity_response(
                detail=_("A user with the email already exists")
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=SubuserAccountSerializer)
    @action(methods=["POST"], detail=False, url_name="add_user", url_path="add-user")
    def add_user(self, request: Request, *args, **kwargs) -> Response:
        try:
            serializer = SubuserAccountSerializer(
                data=request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except IntegrityError:
            return duplicate_entity_response(
                detail=_("A user with the email already exists")
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=ResidentImportedDataSerializer)
    @action(
        methods=["POST"],
        detail=False,
        url_name="import_members",
        url_path="import-members",
        permission_classes=[IsClusterAdmin],
    )
    def import_members(self, request: Request, *args, **kwargs) -> HttpResponseBase:
        importer = GenericModelImporter(
            request=request,
            import_data_serializer_class=ResidentImportedDataSerializer,
            import_serializer_class=ResidentImportExportSerializer,
            is_async=False,
        )
        return importer.get_response()

    @action(
        detail=False,
        methods=["GET"],
        url_path="resident-import-template",
        url_name="resident_import_template",
        permission_classes=[IsClusterAdmin],
    )
    def get_import_template(self, request: Request, *args, **kwargs) -> FileResponse:
        """
        Returns an Excel template file to serve as a starter/guide to users on the format for import
        """
        template_path_prefix = settings.BASE_DIR / "clustr/accounts/assets"
        return GenericModelImporter.serve_template_file(
            request=request,
            template_path_prefix=template_path_prefix,
            name="residents_import_template",
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="approve-account",
        url_name="approve_account",
        permission_classes=[IsClusterAdmin],
    )
    def approve_resident_account(self, request: Request, *args, **kwargs):
        resident = self.get_object()
        resident.approved_by_admin = True
        resident.save(update_fields=["approved_by_admin"])
        return Response(status=status.HTTP_200_OK)
