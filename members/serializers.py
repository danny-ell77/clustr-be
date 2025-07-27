"""
Serializers for the members app.
"""

from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AccountUser
from core.common.models.emergency import EmergencyContact, EmergencyContactType
from accounts.serializers.auth import AuthTokenPairSerializer


class MemberRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for member registration.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    property_owner = serializers.BooleanField(default=False)
    cluster_id = serializers.UUIDField(required=True, write_only=True)

    class Meta:
        model = AccountUser
        fields = [
            "email_address",
            "name",
            "phone_number",
            "unit_address",
            "password",
            "confirm_password",
            "property_owner",
            "cluster_id",
        ]
        extra_kwargs = {
            "phone_number": {"required": True, "allow_blank": False, "editable": True},
            "unit_address": {"required": True},
        }

    def validate(self, attrs):
        """
        Validate that passwords match.
        """
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": _("Password fields didn't match.")}
            )

        # Remove confirm_password from the attributes
        attrs.pop("confirm_password")
        return attrs


class EmergencyContactSerializer(serializers.ModelSerializer):
    """
    Serializer for emergency contacts.
    """

    contact_type = serializers.ChoiceField(choices=EmergencyContactType.choices)

    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "name",
            "phone_number",
            "email",
            "emergency_types",
            "contact_type",
            "is_primary",
            "notes",
        ]
        read_only_fields = ["id"]
        ref_name = "MembersEmergencyContactSerializer"


class MemberLoginSerializer(AuthTokenPairSerializer):
    """
    Serializer for member login.
    Extends the AuthTokenPairSerializer to add device information.
    """

    device_name = serializers.CharField(required=False, write_only=True)
    device_id = serializers.CharField(required=False, write_only=True)
    remember_me = serializers.BooleanField(default=False, write_only=True)
    cluster_id = serializers.UUIDField(required=False, write_only=True)


class PhoneVerificationSerializer(serializers.Serializer):
    """
    Serializer for phone verification.
    """

    phone_number = serializers.CharField(required=True)


class VerifyPhoneSerializer(serializers.Serializer):
    """
    Serializer for verifying phone with OTP.
    """

    phone_number = serializers.CharField(required=True)
    verification_code = serializers.CharField(required=True)


class MemberProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for member profile.
    """

    emergency_contacts = EmergencyContactSerializer(many=True, required=False)

    class Meta:
        model = AccountUser
        fields = [
            "id",
            "name",
            "email_address",
            "phone_number",
            "unit_address",
            "profile_image_url",
            "property_owner",
            "is_verified",
            "is_phone_verified",
            "emergency_contacts",
        ]
        read_only_fields = ["id", "email_address", "is_verified", "is_phone_verified"]
