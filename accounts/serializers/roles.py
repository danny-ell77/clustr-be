from uuid import UUID

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AccountUser, Role, PRIMARY_ROLE_NAME


class PermissionField(serializers.RelatedField):
    def to_representation(self, value: Permission) -> str:
        return str(value.codename)

    def to_internal_value(self, data: str) -> Permission:
        permission = self.get_queryset().filter(codename=data).first()
        if not permission:
            raise serializers.ValidationError(
                {
                    "permissions": _(
                        "Permission with codename: %(code)s does not exist"
                        % {"code": data}
                    )
                }
            )
        return permission

    def get_queryset(self) -> QuerySet:
        content_type = ContentType.objects.get_for_model(AccountUser)
        return Permission.objects.filter(content_type=content_type)


class RoleNameField(serializers.Field):
    def to_representation(self, value: str) -> str:
        return value.partition(":")[-1]

    def to_internal_value(self, data: str) -> str:
        # Role name is prefixed with the owner's id in the model before saving for uniqueness.
        return data


class RoleSerializer(serializers.ModelSerializer):
    name = RoleNameField()
    owner = serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    total_subusers = serializers.IntegerField(read_only=True)
    permissions = PermissionField(many=True, required=False)
    # subusers = SimpleUserSerializer(read_only=True, many=True, source="user_set")

    class Meta:
        model = Role
        fields = [
            "id",
            "owner",
            "name",
            "description",
            "total_subusers",
            "created_at",
            "last_modified_at",
            "permissions",
        ]

    @transaction.atomic
    def create(self, validated_data: dict) -> Role:
        name = validated_data.get("name", None)
        self._validate_primary_role_name(name)
        user: AccountUser = self.context["request"].user
        permissions = validated_data.pop("permissions", [])

        instance: Role = Role.objects.create(
            **validated_data, owner=user.get_owner(), created_by=user.pk
        )

        instance.permissions.set(permissions)
        return instance

    @transaction.atomic
    def update(self, instance: Role, validated_data: dict) -> Role:
        name = instance.name.partition(":")[-1]
        self._validate_primary_role_name(name)
        if permissions := validated_data.pop("permissions", None):
            instance.permissions.set(permissions)

        for key, value in validated_data.items():
            setattr(instance, key, value)

        user_id: UUID = self.context["request"].user.pk
        instance.last_modified_by = user_id
        instance.save()
        return instance

    def _validate_primary_role_name(self, name):
        if name and name == PRIMARY_ROLE_NAME:
            raise serializers.ValidationError(
                {"detail": "Primary user role is readonly"}
            )


class SimpleRoleSerializer(serializers.ModelSerializer):
    name = RoleNameField()
    permissions = PermissionField(many=True, required=False)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]
