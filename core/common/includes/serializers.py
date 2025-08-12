from typing import Type, cast

from rest_framework import serializers
from rest_framework.fields import Field


def build_runtime_serializer(fields: dict[str, Field]) -> Type[serializers.Serializer]:
    new_class = type("RuntimeSerializer", (serializers.Serializer,), fields)
    return cast(Type[serializers.Serializer], new_class)
