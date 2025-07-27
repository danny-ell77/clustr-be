from django.core.signing import BadSignature
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import AccountUser, UserVerification, VerifyMode, VerifyReason
from accounts.serializers import (
    AuthTokenPairSerializer,
    ClusterAdminAccountSerializer,
    ForgotPasswordSerializer,
    OwnerAccountSerializer,
    ResetPasswordSerializer,
)
from accounts.utils import change_password
from core.common.email_sender import NotificationTypes
from core.common.exceptions import CommonAPIErrorCodes, InvalidDataException
from core.common.error_utils import exception_to_response_mapper
from core.common.responses import error_response


class _AuthTokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


AUTH_RESPONSE_SCHEMA = {
    status.HTTP_201_CREATED: _AuthTokenPairSerializer(),
    status.HTTP_400_BAD_REQUEST: "Duplicate entity error",
}


def _get_auth_tokens(email_address: str, password: str) -> dict:
    data = {
        "email_address": email_address,
        "password": password,
    }
    serializer = AuthTokenPairSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class ClusterRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=ClusterAdminAccountSerializer,
        responses=AUTH_RESPONSE_SCHEMA,
        operation_description="Register a new cluster with admin account",
    )
    @exception_to_response_mapper({
        IntegrityError: lambda exc: error_response("DUPLICATE_ENTITY", "Cluster with this name already exists", 400)
    })
    def post(self, request: Request, *args, **kwargs) -> Response:
        try:
            with transaction.atomic():
                serializer = ClusterAdminAccountSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            email_address = serializer.validated_data["admin"]["email_address"]
            password = request.data.get("admin", {}).get("password")
            return Response(
                _get_auth_tokens(email_address=email_address, password=password),
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError:
            return Response(
                {
                    "detail": _(
                        f"{request.data['type']} with this name already exists"
                    ),
                    "code": CommonAPIErrorCodes.DUPLICATE_ENTITY,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ClusterMemberRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=OwnerAccountSerializer,
        responses=AUTH_RESPONSE_SCHEMA,
        operation_description="Register a new cluster member account",
    )
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                serializer = OwnerAccountSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                tokens = _get_auth_tokens(
                    email_address=serializer.data["email_address"],
                    password=serializer.data["password"],
                )
                return Response(tokens, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {
                    "detail": _("This user already exists"),
                    "code": CommonAPIErrorCodes.DUPLICATE_ENTITY,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class SigninView(TokenObtainPairView):
    serializer_class = AuthTokenPairSerializer

    @swagger_auto_schema(
        responses=AUTH_RESPONSE_SCHEMA,
        operation_description="Login endpoint to obtain JWT token pair",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @swagger_auto_schema(
        request_body=ForgotPasswordSerializer,
        responses={
            status.HTTP_200_OK: "Password reset email sent",
            status.HTTP_400_BAD_REQUEST: "Invalid email address",
        },
        operation_description="Request a password reset email",
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_address: str = serializer.validated_data["email_address"]
        verify_mode: VerifyMode = serializer.validated_data["mode"]
        user: AccountUser = AccountUser.objects.filter(
            email_address=email_address
        ).first()
        if not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        UserVerification.for_mode(
            verify_mode, user, VerifyReason.PASSWORD_RESET
        ).send_mail()

        return Response(
            data={"detail": "Password reset email sent"}, status=status.HTTP_200_OK
        )


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @swagger_auto_schema(
        request_body=ResetPasswordSerializer,
        responses={
            status.HTTP_205_RESET_CONTENT: "Password changed successfully",
            status.HTTP_400_BAD_REQUEST: "Invalid token or password",
        },
        operation_description="Reset password using a verification token",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        verification_key = serializer.data["verification_key"]
        verification = _run_verification_key_checks(verification_key)

        user = verification.requested_by
        new_password = serializer.validated_data["password"]
        force_logout = serializer.validated_data["force_logout"]
        change_password(
            user=user,
            new_password=new_password,
            force_logout=force_logout,
        )

        verification.mark_as_verified()
        return Response(
            {"detail": "Password changed successfully"},
            status=status.HTTP_205_RESET_CONTENT,
        )


def _run_verification_key_checks(verification_key):
    token = _infer_signed_token(verification_key)
    verification = UserVerification.objects.filter(
        Q(otp=verification_key) | Q(token=token)
    ).first()
    if not verification:
        raise InvalidDataException(
            detail="This token does not exist",
        )
    if verification.is_expired:
        raise InvalidDataException(
            detail="This token is expired",
        )
    return verification


def _infer_signed_token(verification_key: str):
    token = None
    if len(verification_key) > UserVerification.OTP_MAX_LENGTH:
        try:
            token = UserVerification.unsign_token(
                verification_key,
                reason=NotificationTypes.WEB_TOKEN_PASSWORD_RESET,
            )
        except BadSignature as error:
            raise InvalidDataException(detail=str(error))
    return token


@api_view(["POST"])
@permission_classes([AllowAny])
def check_token_status(request):
    _run_verification_key_checks(request.data.get("token"))
    return Response(
        data={"detail": "Token verified successfully"}, status=status.HTTP_200_OK
    )
