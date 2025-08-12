from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    last_modified_at = serializers.DateTimeField(read_only=True)
    
    def build_field(self, field_name, info, model_class, nested_depth):
        field_class, field_kwargs = super().build_field(field_name, info, model_class, nested_depth)
        field_kwargs.pop('editable', None)  # Remove the problematic parameter
        return field_class, field_kwargs