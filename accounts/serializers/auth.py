from rest_framework import serializers

from accounts.models import VerifyMode


class AuthTokenPairSerializer(serializers.Serializer):
    """
    Serializer for user login credentials.
    """
    email_address = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    remember_me = serializers.BooleanField(default=False, write_only=True, required=False)
    cluster_id = serializers.UUIDField(required=False, write_only=True, allow_null=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email_address = serializers.EmailField(required=True)
    mode = serializers.ChoiceField(
        choices=VerifyMode.choices,
        default=VerifyMode.OTP,
        help_text="The type of key to be used for verification",
    )


class ResetPasswordSerializer(serializers.Serializer):
    verification_key = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    force_logout = serializers.BooleanField(default=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        min_length=8, write_only=True, required=True
    )
    new_password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)
    force_logout = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs.get("new_password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "New passwords do not match."}
            )
        return attrs
