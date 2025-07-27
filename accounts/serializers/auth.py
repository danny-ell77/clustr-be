from typing import Optional

from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import VerifyMode


class AuthTokenPairSerializer(TokenObtainPairSerializer):
    """
    Custom token pair serializer to allow for dynamic refresh token TTL. For people who enabled 'Remember me',
    The token will have a longer TTL which means that the user will stay signed in for longer.
    """

    def __init__(self, data: Optional[dict] = None, *args, **kwargs):
        if data:
            remember_me = data.pop("remember_me", False)
            if remember_me:
                self.token_class.lifetime = settings.REFRESH_TOKEN_LIFETIME
            else:
                self.token_class.lifetime = (
                    settings.REFRESH_TOKEN_LIFETIME_WITH_REMEMBER_ME
                )
        super().__init__(data=data, *args, **kwargs)


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
    force_logout = serializers.BooleanField(default=False)
