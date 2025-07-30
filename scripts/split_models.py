#!/usr/bin/env python3
"""
Generic Model Splitter Script for Django Models

This script analyzes Django model files and splits each model class and related choices
into separate files, then updates the __init__.py to maintain backward compatibility.

Usage:
    python scripts/split_models.py [model_file_or_directory] [options]
    
Examples:
    python scripts/split_models.py core/common/models/wallet.py
    python scripts/split_models.py core/common/models/task.py
    python scripts/split_models.py core/common/models/  # Process all models in directory
"""

import os
import re
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional


class GenericModelSplitter:
    """Generic model splitter that can handle any Django model file."""
    
    def __init__(self, source_file: str, target_dir: str = None, create_subdirs: bool = True):
        self.source_file = Path(source_file)
        self.source_name = self.source_file.stem
        
        # Determine target directory
        if target_dir:
            self.target_dir = Path(target_dir)
        else:
            if create_subdirs:
                self.target_dir = self.source_file.parent / self.source_name
            else:
                self.target_dir = self.source_file.parent
        
        self.models_info = {}
        self.imports = []
        self.file_header = ""
        self.create_subdirs = create_subdirs
        
    def analyze_source_file(self):
        """Analyze the source file to extract models and their dependencies."""
        with open(self.source_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract file header (imports and module docstring)
        lines = content.split('\n')
        header_end = 0
        
        # Find where classes start
        for i, line in enumerate(lines):
            if line.strip().startswith('class ') and ':' in line:
                header_end = i
                break
                
        self.file_header = '\n'.join(lines[:header_end])
        self.extract_imports_from_header()
        
        # Parse the AST to find classes and their relationships
        tree = ast.parse(content)
        
        # Only process top-level classes, not nested classes like Meta
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                model_info = self.extract_model_info(node, content, lines)
                self.models_info[node.name] = model_info
    
    def extract_imports_from_header(self):
        """Extract import statements from the file header."""
        self.imports = []
        for line in self.file_header.split('\n'):
            if line.strip().startswith(('import ', 'from ')):
                self.imports.append(line.strip())
    
    def extract_model_info(self, node: ast.ClassDef, content: str, lines: List[str]) -> Dict:
        """Extract information about a model class."""
        start_line = node.lineno - 1
        
        # Find the end of the class by looking for next class or end of file
        end_line = len(lines)
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip():
                current_indent = len(line) - len(line.lstrip())
                # If we find a line at the same or lower indentation level that starts a new class/function
                if (current_indent <= indent_level and 
                    line.strip().startswith(('class ', 'def ', '@'))):
                    end_line = i
                    break
        
        class_content = '\n'.join(lines[start_line:end_line])
        
        # Determine model type and dependencies
        is_choices_class = self.is_choices_class(node)
        is_model_class = self.is_model_class(node)
        
        # Extract related models by looking for ForeignKey relationships
        related_models = self.find_foreign_key_references(class_content)
        
        return {
            'name': node.name,
            'content': class_content,
            'start_line': start_line,
            'end_line': end_line,
            'is_choices': is_choices_class,
            'is_model': is_model_class,
            'related_models': related_models,
            'dependencies': self.find_class_dependencies(class_content)
        }
    
    def is_choices_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is a Django choices class."""
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr in ['TextChoices', 'IntegerChoices', 'Choices']:
                    return True
            elif isinstance(base, ast.Name):
                if base.id in ['TextChoices', 'IntegerChoices', 'Choices']:
                    return True
        return False
    
    def is_model_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is a Django model class."""
        for base in node.bases:
            if isinstance(base, ast.Name):
                if 'Model' in base.id:
                    return True
            elif isinstance(base, ast.Attribute):
                if 'Model' in base.attr:
                    return True
        return False
    
    def find_foreign_key_references(self, content: str) -> Set[str]:
        """Find ForeignKey references in model content."""
        related_models = set()
        
        # Look for ForeignKey patterns
        patterns = [
            r'models\.ForeignKey\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)',
            r'models\.OneToOneField\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)',
            r'models\.ManyToManyField\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                model_name = match.group(1)
                if not model_name.startswith(("'", '"')):  # Skip string references
                    related_models.add(model_name)
        
        return related_models
    
    def find_class_dependencies(self, content: str) -> Set[str]:
        """Find class dependencies within the content."""
        dependencies = set()
        
        # Look for class references (typically choices classes)
        class_patterns = [
            r'\b([A-Z][A-Za-z0-9_]*(?:Status|Type|Priority|Category|Frequency|Severity))\b',
            r'choices=([A-Z][A-Za-z0-9_]+)\.choices',
            r'default=([A-Z][A-Za-z0-9_]+)\.',
        ]
        
        for pattern in class_patterns:
            for match in re.finditer(pattern, content):
                class_name = match.group(1)
                if class_name != match.group(0):  # Avoid self-references
                    dependencies.add(class_name)
        
        return dependencies
    
    def group_related_models(self) -> dict[str, List[str]]:
        """Auto-group related models that should be in the same file."""
        groups = {}
        processed = set()
        
        # First, handle predefined groupings for known files
        if self.source_name in self.get_predefined_groupings():
            return self.get_predefined_groupings()[self.source_name]
        
        # Auto-group based on naming patterns and relationships
        for model_name, model_info in self.models_info.items():
            if model_name in processed:
                continue
                
            group_name = self.determine_group_name(model_name, model_info)
            
            if group_name not in groups:
                groups[group_name] = []
            
            # Add the model and its closely related models
            related_group = self.find_related_models_for_grouping(model_name, model_info)
            for related_model in related_group:
                if related_model not in processed:
                    groups[group_name].append(related_model)
                    processed.add(related_model)
        
        # Sort models within groups (choices classes first, then models)
        for group_name in groups:
            groups[group_name].sort(key=lambda x: (
                not self.models_info.get(x, {}).get('is_choices', False),  # Choices first
                x  # Then alphabetical
            ))
        
        return groups
    
    def get_predefined_groupings(self) -> dict[str, dict[str, List[str]]]:
        """Get predefined groupings for known model files."""
        return {
            'wallet': {
                'wallet': ['WalletStatus', 'Wallet'],
                'transaction': ['TransactionType', 'TransactionStatus', 'PaymentProvider', 'Transaction'],
                'payment_error': ['PaymentErrorType', 'PaymentErrorSeverity', 'PaymentError'],
                'bill': ['BillType', 'BillStatus', 'Bill'],
                'recurring_payment': ['RecurringPaymentStatus', 'RecurringPaymentFrequency', 'RecurringPayment']
            },
            'task': {
                'task': ['TaskType', 'TaskStatus', 'TaskPriority', 'Task'],
                'task_assignment': ['TaskAssignment', 'TaskAssignmentHistory'],
                'task_attachment': ['TaskAttachment'],
                'task_history': ['TaskStatusHistory', 'TaskEscalationHistory'],
                'task_comment': ['TaskComment']
            },
            'announcement': {
                'announcement': ['AnnouncementCategory', 'Announcement'],
                'announcement_interaction': ['AnnouncementView', 'AnnouncementLike', 'AnnouncementComment'],
                'announcement_content': ['AnnouncementAttachment'],
                'announcement_tracking': ['AnnouncementReadStatus']
            },
            # Add more predefined groupings as needed
        }
    
    def determine_group_name(self, model_name: str, model_info: dict) -> str:
        """Determine the appropriate group name for a model."""
        # Remove common suffixes to find base name
        base_name = model_name
        
        suffixes = ['Status', 'Type', 'Priority', 'Category', 'Frequency', 'Severity', 'Error']
        for suffix in suffixes:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
                break
        
        # Convert CamelCase to snake_case
        group_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', base_name).lower()
        
        # Handle compound names
        if not group_name or group_name == 'base':
            group_name = model_name.lower()
        
        return group_name
    
    def find_related_models_for_grouping(self, model_name: str, model_info: dict) -> List[str]:
        """Find models that should be grouped with the given model."""
        related = [model_name]
        
        # Group choices classes with their corresponding models
        if model_info['is_choices']:
            # Find models that use this choices class
            for other_name, other_info in self.models_info.items():
                if model_name in other_info['dependencies']:
                    related.append(other_name)
        elif model_info['is_model']:
            # Find choices classes that this model uses
            for dep in model_info['dependencies']:
                if dep in self.models_info and self.models_info[dep]['is_choices']:
                    related.append(dep)
        
        return related
    
    def create_model_files(self):
        """Create individual model files."""
        groups = self.group_related_models()
        
        print(f"\nGrouping strategy:")
        for group_name, models in groups.items():
            print(f"  {group_name}: {models}")
        
        # Create the target directory if it doesn't exist
        os.makedirs(self.target_dir, exist_ok=True)
        
        for group_name, model_names in groups.items():
            self.create_single_model_file(group_name, model_names)
        
        # Update __init__.py
        self.update_init_file(groups)
    
    def create_single_model_file(self, group_name: str, model_names: List[str]):
        """Create a single model file for a group of related models."""
        file_path = self.target_dir / f"{group_name}.py"
        
        # Collect all models for this file
        models_content = []
        imports_needed = set()
        
        for model_name in model_names:
            if model_name in self.models_info:
                model_info = self.models_info[model_name]
                models_content.append(model_info['content'])
                imports_needed.update(model_info['dependencies'])
        
        # Remove self-references
        imports_needed = imports_needed - set(model_names)
        
        # Generate file content
        content_parts = []
        
        # Add file header
        content_parts.append(f'"""\n{group_name.replace("_", " ").title()} models for ClustR application.\n"""')
        content_parts.append('')
        
        # Add basic imports
        basic_imports = [
            'import uuid',
            'import logging', 
            'from decimal import Decimal',
            'from django.db import models',
            'from django.utils.translation import gettext_lazy as _',
            'from django.core.validators import MinValueValidator',
            'from django.utils import timezone'
        ]
        
        # Only add imports that are actually used in the original file
        for imp in basic_imports:
            if any(keyword in ' '.join(models_content) for keyword in imp.split()[1:]):
                content_parts.append(imp)
        
        content_parts.append('')
        content_parts.append('from core.common.models.base import AbstractClusterModel')
        
        # Add imports for related models from other groups
        if imports_needed:
            content_parts.append('')
            content_parts.append('# Related model imports (will be converted to string references)')
            for related_model in sorted(imports_needed):
                if related_model not in model_names:
                    content_parts.append(f'# from core.common.models.{self.source_name}.{self.get_file_for_model(related_model)} import {related_model}')
        
        content_parts.append('')
        content_parts.append("logger = logging.getLogger('clustr')")
        content_parts.append('')
        content_parts.append('')
        
        # Add models
        content_parts.extend(models_content)
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
        
        print(f"Created {file_path}")
    
    def get_file_for_model(self, model_name: str) -> str:
        """Get the filename that contains a specific model."""
        groups = self.group_related_models()
        for group_name, model_names in groups.items():
            if model_name in model_names:
                return group_name
        return 'unknown'
    
    def update_init_file(self, groups: dict[str, List[str]]):
        """Update the __init__.py file to maintain backward compatibility."""
        init_file = self.target_dir / '__init__.py'
        
        content_parts = []
        content_parts.append('"""')
        content_parts.append(f'{self.source_name.title()} models package for core.common.')
        content_parts.append('"""')
        content_parts.append('')
        
        # Add imports from each file
        all_exports = []
        
        for group_name, model_names in groups.items():
            imports = []
            for model_name in model_names:
                if model_name in self.models_info:
                    imports.append(model_name)
                    all_exports.append(model_name)
            
            if imports:
                content_parts.append(f'from core.common.models.{self.source_name}.{group_name} import (')
                for imp in imports:
                    content_parts.append(f'    {imp},')
                content_parts.append(')')
        
        content_parts.append('')
        content_parts.append('__all__ = [')
        for export in sorted(all_exports):
            content_parts.append(f'    "{export}",')
        content_parts.append(']')
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
        
        print(f"Updated {init_file}")
    
    def fix_circular_imports(self):
        """Fix circular import issues by using string references."""
        groups = self.group_related_models()
        
        for group_name, model_names in groups.items():
            file_path = self.target_dir / f"{group_name}.py"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated_content = content
            
            # Replace ForeignKey references with string references for models in other groups
            for other_group, other_models in groups.items():
                if other_group != group_name:
                    for other_model in other_models:
                        if other_model in self.models_info and self.models_info[other_model]['is_model']:
                            # Replace direct model references with string references
                            patterns = [
                                (rf'models\.ForeignKey\s*\(\s*{other_model}', f"models.ForeignKey('{other_model}'"),
                                (rf'models\.OneToOneField\s*\(\s*{other_model}', f"models.OneToOneField('{other_model}'"),
                                (rf'models\.ManyToManyField\s*\(\s*{other_model}', f"models.ManyToManyField('{other_model}'"),
                            ]
                            
                            for pattern, replacement in patterns:
                                updated_content = re.sub(pattern, replacement, updated_content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
    
    def run(self):
        """Run the complete splitting process."""
        print(f"Analyzing {self.source_file}...")
        self.analyze_source_file()
        
        print(f"Found {len(self.models_info)} models/choices classes")
        for name, info in self.models_info.items():
            model_type = "Choices" if info['is_choices'] else "Model" if info['is_model'] else "Other"
            print(f"  - {name} ({model_type})")
        
        print(f"\nCreating individual model files in {self.target_dir}...")
        self.create_model_files()
        
        print("\nFixing circular imports...")
        self.fix_circular_imports()
        
        print("\nDone! Models have been split into individual files.")
        print("\nNext steps:")
        print(f"1. Review the generated files in {self.target_dir}")
        print("2. Update the main models/__init__.py to import from the new package:")
        print(f"   from core.common.models.{self.source_name} import *")
        print("3. Test that all existing imports still work")
        print("4. Run Django's makemigrations and migrate if needed")
        print("5. Remove or rename the original file after testing")


def process_single_file(file_path: str, target_dir: str = None):
    """Process a single model file."""
    if not os.path.exists(file_path):
        print(f"File {file_path} not found!")
        return False
    
    splitter = GenericModelSplitter(file_path, target_dir)
    splitter.run()
    return True


def process_directory(directory_path: str):
    """Process all model files in a directory."""
    directory = Path(directory_path)
    if not directory.exists():
        print(f"Directory {directory_path} not found!")
        return
    
    model_files = list(directory.glob("*.py"))
    # Exclude __init__.py and base.py
    model_files = [f for f in model_files if f.name not in ['__init__.py', 'base.py']]
    
    print(f"Found {len(model_files)} model files to process:")
    for file in model_files:
        print(f"  - {file.name}")
    
        for file_path in model_files:
            print(f"\n{'='*60}")
            print(f"Processing {file_path.name}")
            print('='*60)
        try:
            process_single_file(str(file_path))
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
            continue


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description='Split Django model files into individual model files')
    parser.add_argument('source', help='Source model file or directory path')
    parser.add_argument('--target', '-t', help='Target directory (optional)')
    parser.add_argument('--no-subdirs', action='store_true', help="Don't create subdirectories")
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    
    if source_path.is_file():
        print(f"Processing single file: {source_path}")
        process_single_file(str(source_path), args.target)
    elif source_path.is_dir():
        print(f"Processing directory: {source_path}")
        process_directory(str(source_path))
    else:
        print(f"Path {args.source} does not exist!")
        return 1
    
    return 0


if __name__ == "__main__":
    # If no arguments provided, default to wallet.py for backwards compatibility
    import sys
    if len(sys.argv) == 1:
        source_file = "core/common/models/wallet.py"
        if os.path.exists(source_file):
            print("No arguments provided, defaulting to wallet.py")
            process_single_file(source_file)
        else:
            print("Usage: python scripts/split_models.py <source_file_or_directory>")
            print("Example: python scripts/split_models.py core/common/models/wallet.py")
    else:
        exit(main())
