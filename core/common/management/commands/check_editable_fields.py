from django.core.management.base import BaseCommand
from django.apps import apps
from rest_framework import serializers

class Command(BaseCommand):
    help = 'Find model fields with editable=False that might cause DRF issues'
    
    def handle(self, *args, **options):
        print("=== Fields with editable=False ===")
        problematic_fields = []
        
        for model in apps.get_models():
            model_name = model.__name__
            for field in model._meta.fields:
                if hasattr(field, 'editable') and field.editable is False:
                    field_info = f"{model_name}.{field.name} ({field.__class__.__name__})"
                    print(field_info)
                    problematic_fields.append((model, field.name, field.__class__.__name__))
        
        print(f"\nFound {len(problematic_fields)} fields with editable=False")
        
        # Check if any of these are in Bill model specifically
        bill_fields = [fname for m, fname, ftype in problematic_fields if m.__name__ == 'Bill']
        if bill_fields:
            print(f"\nBill model has {len(bill_fields)} editable=False fields")
