import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

DOMAIN_PATTERN = r"^(?:https?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"


class LenientURLField(serializers.CharField):
    """
    A custom URL field that ensures the value is a valid URL but not
    necessarily an FQDN. If the value is not a FQDN, the prefix "https://"
    is prepended to it.
    """

    def to_representation(self, value):
        return value

    def to_internal_value(self, value):
        self._validate(value)
        value = self._get_value_with_protocol(value)
        return value

    def _validate(self, value):
        match = re.search(DOMAIN_PATTERN, value)
        if not match:
            raise serializers.ValidationError(_(f"Invalid URL - {value}"))

    def _get_value_with_protocol(self, value):
        if not value.startswith("http"):
            return f"https://{value}"
        return value
