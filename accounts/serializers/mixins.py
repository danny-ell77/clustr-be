from rest_framework import serializers


class NameSplitMixin:
    """Split name field into first_name/last_name at API boundary. Keeps name for backward compatibility."""
    
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True, read_only=True)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'name') and instance.name:
            parts = instance.name.split(maxsplit=1)
            data['first_name'] = parts[0] if parts else ''
            data['last_name'] = parts[1] if len(parts) > 1 else ''
            data['name'] = instance.name
        else:
            data['first_name'] = ''
            data['last_name'] = ''
            data['name'] = ''
        return data
    
    def to_internal_value(self, data):
        if 'first_name' in data or 'last_name' in data:
            first = data.pop('first_name', '').strip()
            last = data.pop('last_name', '').strip()
            data['name'] = f"{first} {last}".strip()
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'name' in attrs and not attrs['name'].strip():
            raise serializers.ValidationError({
                'first_name': 'At least first name is required'
            })
        return attrs
