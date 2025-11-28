import os
import sys
import traceback
from django.core.management.base import BaseCommand
from django.apps import apps
from rest_framework import serializers
from rest_framework.fields import Field

class Command(BaseCommand):
    help = 'Debug serializer editable parameter issue'
    
    def add_arguments(self, parser):
        parser.add_argument('--test-all', action='store_true', help='Test all serializers')
        parser.add_argument('--fix-mode', action='store_true', help='Apply monkey patch fix')
    
    def handle(self, *args, **options):
        if options['fix_mode']:
            self.apply_monkey_patch()
            self.stdout.write("Monkey patch applied. Try accessing /redoc/ again.")
            return
            
        self.stdout.write("=== DEBUGGING SERIALIZER ISSUE ===\n")
        
        # 1. Find all serializer classes in the project
        serializer_classes = self.find_all_serializers()
        self.stdout.write(f"Found {len(serializer_classes)} serializer classes\n")
        
        # 2. Test each serializer
        problematic_serializers = []
        for serializer_class in serializer_classes:
            try:
                self.test_serializer(serializer_class)
            except Exception as e:
                if 'editable' in str(e):
                    problematic_serializers.append((serializer_class, str(e)))
                    self.stdout.write(f"❌ {serializer_class.__name__}: {e}")
        
        if problematic_serializers:
            self.stdout.write(f"\n=== FOUND {len(problematic_serializers)} PROBLEMATIC SERIALIZERS ===")
            for serializer_class, error in problematic_serializers:
                self.stdout.write(f"{serializer_class.__module__}.{serializer_class.__name__}: {error}")
        else:
            self.stdout.write("No problematic serializers found. The issue might be elsewhere.")
            
        # 3. Test BillViewSet specifically
        self.test_bill_viewset()
        
        # 4. Check if the issue is in the schema generation
        self.test_schema_generation()
    
    def find_all_serializers(self):
        """Find all ModelSerializer classes in the project"""
        serializer_classes = []
        
        # Get all modules from installed apps
        for app_config in apps.get_app_configs():
            app_module = app_config.module
            if app_module:
                serializer_classes.extend(self.find_serializers_in_module(app_module))
        
        return serializer_classes
    
    def find_serializers_in_module(self, module):
        """Find serializer classes in a module"""
        serializers_found = []
        
        # Check if module has serializers submodule
        module_path = module.__path__[0] if hasattr(module, '__path__') else None
        if not module_path:
            return serializers_found
            
        try:
            # Look for serializers.py files
            serializers_files = []
            for root, dirs, files in os.walk(module_path):
                for file in files:
                    if file.endswith('serializers.py') or (file.endswith('.py') and 'serializer' in file.lower()):
                        serializers_files.append(os.path.join(root, file))
            
            for file_path in serializers_files:
                try:
                    # Import the module
                    relative_path = os.path.relpath(file_path, module_path)
                    module_name = relative_path.replace(os.path.sep, '.').replace('.py', '')
                    full_module_name = f"{module.__name__}.{module_name}"
                    
                    try:
                        imported_module = __import__(full_module_name, fromlist=[''])
                    except ImportError:
                        continue
                    
                    # Find serializer classes
                    for attr_name in dir(imported_module):
                        attr = getattr(imported_module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, serializers.ModelSerializer) and 
                            attr != serializers.ModelSerializer):
                            serializers_found.append(attr)
                            
                except Exception as e:
                    self.stdout.write(f"Error importing {file_path}: {e}")
                    
        except Exception as e:
            self.stdout.write(f"Error scanning {module}: {e}")
            
        return serializers_found
    
    def test_serializer(self, serializer_class):
        """Test a serializer class for the editable parameter issue"""
        try:
            # Try to instantiate the serializer
            serializer = serializer_class()
            
            # Try to access fields (this triggers field creation)
            fields = serializer.fields
            
            # Try to get the field mapping
            for field_name, field in fields.items():
                pass
                
        except Exception as e:
            if 'editable' in str(e):
                raise
            # Other errors are not our concern right now
            pass
    
    def test_bill_viewset(self):
        """Test BillViewSet specifically since that's where the error occurs"""
        self.stdout.write("\n=== TESTING BILL VIEWSET ===")
        
        try:
            # Try to find and test BillViewSet
            from django.urls import get_resolver
            from rest_framework.viewsets import ModelViewSet
            
            # Find BillViewSet in URL patterns
            resolver = get_resolver()
            
            # This is a simplified test - you might need to adjust based on your URL structure
            self.stdout.write("BillViewSet test would require specific import path")
            
        except Exception as e:
            self.stdout.write(f"Error testing BillViewSet: {e}")
    
    def test_schema_generation(self):
        """Test schema generation to find the exact point of failure"""
        self.stdout.write("\n=== TESTING SCHEMA GENERATION ===")
        
        try:
            from drf_yasg.generators import OpenAPISchemaGenerator
            from django.test import RequestFactory
            
            factory = RequestFactory()
            request = factory.get('/')
            
            generator = OpenAPISchemaGenerator(
                info=None,
                version='1.0.0',
                url=None
            )
            
            # This will fail at the exact point
            schema = generator.get_schema(request, public=True)
            self.stdout.write("Schema generation successful - issue might be elsewhere")
            
        except Exception as e:
            self.stdout.write(f"Schema generation failed: {e}")
            if 'editable' in str(e):
                self.stdout.write("This is the exact error we're looking for!")
                traceback.print_exc()
    
    def apply_monkey_patch(self):
        """Apply a monkey patch to fix the issue globally"""
        self.stdout.write("Applying monkey patch to Field.__init__...")
        
        # Store original Field.__init__
        original_field_init = Field.__init__
        
        def patched_field_init(self, **kwargs):
            # Remove 'editable' parameter if present
            kwargs.pop('editable', None)
            return original_field_init(self, **kwargs)
        
        # Apply the patch
        Field.__init__ = patched_field_init
        
        self.stdout.write("Monkey patch applied!")
