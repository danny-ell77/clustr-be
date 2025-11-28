#!/usr/bin/env python3
"""
Script to replace serializers.ModelSerializer with BaseModelSerializer
and add the necessary import to all Python files.
"""

import os
import re
import argparse
from pathlib import Path

def find_python_files(directory):
    """Find all Python files in the directory and subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip common directories that don't contain serializers
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                python_files.append(file_path)
    return python_files

def has_model_serializer(file_path):
    """Check if file contains serializers.ModelSerializer usage."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for serializers.ModelSerializer pattern
            return 'serializers.ModelSerializer' in content
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def process_file(file_path, base_serializer_import, dry_run=False):
    """Process a single file to replace ModelSerializer with BaseSerializer."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        changes_made = []
        
        # Check if file already has the BaseModelSerializer import
        base_import_pattern = r'from\s+.*\s+import\s+.*BaseModelSerializer'
        has_base_import = re.search(base_import_pattern, content)
        
        # 1. Add BaseModelSerializer import if not present
        if not has_base_import:
            # Find existing DRF imports
            drf_import_pattern = r'(from\s+rest_framework\s+import\s+[^n].*?)(?=\n)'
            drf_match = re.search(drf_import_pattern, content)
            
            if drf_match:
                # Add to existing DRF import
                existing_import = drf_match.group(1)
                if 'serializers' in existing_import:
                    # Add after existing DRF import
                    insertion_point = drf_match.end()
                    content = (content[:insertion_point] + 
                             f'\n{base_serializer_import}' + 
                             content[insertion_point:])
                    changes_made.append("Added BaseModelSerializer import")
                else:
                    # Insert at the beginning of imports
                    import_section = find_import_section(content)
                    content = (content[:import_section] + 
                             f'{base_serializer_import}\n' + 
                             content[import_section:])
                    changes_made.append("Added BaseModelSerializer import at top")
            else:
                # No existing DRF import, add at the beginning of imports
                import_section = find_import_section(content)
                content = (content[:import_section] + 
                         f'{base_serializer_import}\n' + 
                         content[import_section:])
                changes_made.append("Added BaseModelSerializer import (new)")
        
        # 2. Replace serializers.ModelSerializer with BaseModelSerializer
        # Pattern to match class definitions
        class_pattern = r'class\s+(\w+)\s*\(\s*(.*?)serializers\.ModelSerializer(.*?)\s*\):'
        
        def replace_inheritance(match):
            class_name = match.group(1)
            before_model_serializer = match.group(2)
            after_model_serializer = match.group(3)
            
            # Clean up the inheritance
            before = before_model_serializer.strip().rstrip(',').strip()
            after = after_model_serializer.strip().lstrip(',').strip()
            
            # Build new inheritance
            new_inheritance = []
            if before:
                new_inheritance.append(before)
            new_inheritance.append('BaseModelSerializer')
            if after:
                new_inheritance.append(after)
            
            return f'class {class_name}({", ".join(new_inheritance)}):'
        
        new_content = re.sub(class_pattern, replace_inheritance, content)
        
        if new_content != content:
            changes_made.append("Replaced ModelSerializer inheritance")
            content = new_content
        
        # 3. Write changes if any were made and not dry run
        if content != original_content:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return changes_made
        else:
            return []
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def find_import_section(content):
    """Find where to insert imports (after existing imports)."""
    lines = content.split('\n')
    import_end = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(('import ', 'from ')) and not stripped.startswith('#'):
            import_end = i + 1
        elif stripped == '' and import_end > 0:
            # Empty line after imports
            continue
        elif stripped.startswith('#') and import_end == 0:
            # Skip initial comments/docstrings
            continue
        elif stripped != '' and import_end > 0:
            # Non-empty line after imports, this is where we insert
            break
    
    # Convert line number back to character position
    return len('\n'.join(lines[:import_end])) + (1 if import_end > 0 else 0)

def main():
    parser = argparse.ArgumentParser(description='Replace serializers.ModelSerializer with BaseModelSerializer')
    parser.add_argument('directory', help='Directory to scan for Python files')
    parser.add_argument('--base-import', default='from core.common.serializers.base import BaseModelSerializer',
                       help='Import statement for BaseModelSerializer')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--exclude', nargs='*', default=['migrations', 'tests', '__pycache__', '.venv'],
                       help='Directories to exclude')
    
    args = parser.parse_args()
    
    print(f"Scanning directory: {args.directory}")
    print(f"Base import: {args.base_import}")
    print(f"Dry run: {args.dry_run}")
    print(f"Excluding: {args.exclude}")
    print("-" * 50)
    
    # Find all Python files
    python_files = find_python_files(args.directory)
    
    # Filter out excluded directories
    filtered_files = []
    for file_path in python_files:
        exclude_file = False
        for exclude_dir in args.exclude:
            if exclude_dir in file_path:
                exclude_file = True
                break
        if not exclude_file:
            filtered_files.append(file_path)
    
    print(f"Found {len(filtered_files)} Python files to check")
    print("-" * 50)
    
    # Process files that contain ModelSerializer
    processed_count = 0
    changed_count = 0
    
    for file_path in filtered_files:
        if has_model_serializer(file_path):
            print(f"Processing: {file_path}")
            changes = process_file(file_path, args.base_import, args.dry_run)
            
            if changes:
                changed_count += 1
                for change in changes:
                    print(f"  ✓ {change}")
            else:
                print(f"  - No changes needed")
            
            processed_count += 1
            print()
    
    print("-" * 50)
    print(f"Summary:")
    print(f"Files processed: {processed_count}")
    print(f"Files changed: {changed_count}")
    
    if args.dry_run:
        print("\nThis was a dry run. Use without --dry-run to make actual changes.")
    else:
        print("\nChanges have been applied!")
        print("\nDon't forget to:")
        print("1. Create the BaseModelSerializer class in utils/serializers.py")
        print("2. Test your application")
        print("3. Run your tests")

if __name__ == '__main__':
    main()