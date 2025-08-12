from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.template import Context
from rest_framework import serializers

from accounts.models import AccountUser, UserVerification, VerifyReason, VerifyMode
from accounts.serializers.roles import PermissionField
from core.notifications.events import NotificationEvents
from core.common.includes import notifications
from core.common.models import Cluster


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountUser
        fields = [
            "email_address",
            "name",
            "phone_number",
            "profile_image_url",
            "is_verified",
        ]
        read_only_fields = ["is_verified"]


class OwnerAccountSerializer(AccountSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    property_owner = serializers.BooleanField(default=False)

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ["password", "property_owner"]

    def create(self, validated_data):
        email_address = validated_data.pop("email_address")
        password = validated_data.pop("password")
        user = AccountUser.objects.create_owner(
            email_address,
            password,
            **validated_data,
        )
        self._send_owner_onboarding_email(user)
        return user

    def _send_owner_onboarding_email(self, user: AccountUser):
        verification = UserVerification.generate_otp(
            user=user, reason=VerifyReason.ONBOARDING
        )
        verification.send_mail()


class SubuserAccountSerializer(AccountSerializer):
    permissions = PermissionField(many=True, required=False, allow_null=True)

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ["permissions"]

    def create(self, validated_data: dict) -> AccountUser:
        permissions = validated_data.pop("permissions", [])
        owner = self.context["request"].user
        user = AccountUser.objects.create_subuser(
            owner, permissions=permissions, **validated_data
        )
        self._send_subuser_onboarding_email(user)
        self._notify_owner_via_email(user)
        return user

    def _send_subuser_onboarding_email(self, user: AccountUser) -> None:
        verification = UserVerification.generate_otp(
            user=user, reason=VerifyReason.ONBOARDING
        )
        verification.send_mail()

    def _notify_owner_via_email(self, user: AccountUser):
        notifications.send(
            event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for NEW_SUBUSER_ACCOUNT_TO_OWNER
            recipients=[user.get_owner()],
            cluster=user.cluster,
            context={"owner": user.get_owner().name, "user": user.name},
        )


class StaffAccountSerializer(AccountSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        source="groups",
        queryset=Group.objects.all(),
        allow_null=True,
    )

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ["roles"]

    def create(self, validated_data: dict):
        roles = validated_data.pop("groups", None)
        email_address = validated_data.pop("email_address")
        owner = self.context["request"].user
        user = AccountUser.objects.create_staff(
            owner, email_address, roles, **validated_data
        )
        self._send_staff_onboarding_email(user)
        self._notify_owner_via_email(user)
        return user

    def _send_staff_onboarding_email(self, user: AccountUser):
        verification: UserVerification = UserVerification.generate_token(
            user=user,
            reason=VerifyReason.ONBOARDING,
        )
        verification.send_mail()

    def _notify_owner_via_email(self, user: AccountUser):
        notifications.send(
            event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for NEW_SUBUSER_ACCOUNT_TO_OWNER
            recipients=[user.get_owner()],
            cluster=user.cluster,
            context={"owner": user.get_owner().name, "user": user.name},
        )


class ClusterAdminAccountSerializer(serializers.ModelSerializer):
    admin = OwnerAccountSerializer(required=True)

    class Meta:
        model = Cluster
        fields = ["type", "name", "admin"]

    @transaction.atomic
    def create(self, validated_data: dict) -> Cluster:
        admin = self._create_admin_account(validated_data.pop("admin"))
        cluster = self._create_cluster(validated_data, admin)
        self._send_onboarding_email(user=admin)
        return cluster

    def _create_cluster(self, data, admin) -> Cluster:
        return Cluster.objects.create(**data, owner_id=admin.pk)

    def _create_admin_account(self, data) -> AccountUser:
        return AccountUser.objects.create_admin(**data)

    def _send_onboarding_email(self, user: AccountUser):
        notifications.send(
            event=NotificationEvents.SYSTEM_UPDATE, # Placeholder for NEW_ADMIN_ONBOARDING
            recipients=[user],
            cluster=user.cluster, # Assuming user has a cluster attribute
            context={
                "admin_name": user.name,
            }
        )


class UserSummarySerializer(serializers.ModelSerializer):
    """Serializer for user summary information"""
    
    class Meta:
        model = AccountUser
        fields = [
            'id',
            'name',
            'email_address',
            'profile_image_url',
        ]
        read_only_fields = ['id', 'name', 'email_address', 'profile_image_url']


class EmailVerificationSerializer(serializers.Serializer):
    email_address = serializers.EmailField()
    verify_mode = serializers.ChoiceField(
        choices=[VerifyMode.OTP.value, VerifyMode.TOKEN.value]
    )
