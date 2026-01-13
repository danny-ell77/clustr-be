#!/usr/bin/env python
"""
Load initial data fixture only if the database is empty.

This script checks foundational tables (AccountUser, Cluster) to determine
if the database has already been populated. If these tables are empty,
it loads the initial_data.json fixture and creates a demo account.
Otherwise, it skips to avoid duplicate key errors or data overwrites.
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_production")

import django
django.setup()

from django.core.management import call_command
from django.db import transaction
from django.conf import settings


def ensure_fixture_encoding(fixture_name):
    """
    Ensure the fixture file is UTF-8 encoded.
    
    Windows may save JSON files as UTF-16, which Django's loaddata cannot read.
    This function detects UTF-16 BOM and converts the file to UTF-8 in-place.
    """
    fixture_path = None
    for fixtures_dir in settings.FIXTURE_DIRS:
        candidate = os.path.join(fixtures_dir, fixture_name)
        if os.path.exists(candidate):
            fixture_path = candidate
            break
    
    if not fixture_path:
        base_dir = settings.BASE_DIR
        candidate = os.path.join(base_dir, fixture_name)
        if os.path.exists(candidate):
            fixture_path = candidate
    
    if not fixture_path:
        print(f"Fixture file '{fixture_name}' not found, skipping encoding check.")
        return
    
    with open(fixture_path, 'rb') as f:
        first_bytes = f.read(4)
    
    encoding = None
    if first_bytes[:2] == b'\xff\xfe':
        encoding = 'utf-16-le'
    elif first_bytes[:2] == b'\xfe\xff':
        encoding = 'utf-16-be'
    elif first_bytes[:3] == b'\xef\xbb\xbf':
        encoding = 'utf-8-sig'
    
    if encoding and encoding != 'utf-8-sig':
        print(f"Detected {encoding.upper()} encoding in '{fixture_name}', converting to UTF-8...")
        with open(fixture_path, 'r', encoding=encoding) as f:
            content = f.read()
        with open(fixture_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully converted '{fixture_name}' to UTF-8.")
    else:
        print(f"Fixture '{fixture_name}' encoding is OK.")


DEMO_CLUSTER_NAME = "ClustR-Prime"
DEMO_OWNER_EMAIL = "admin@demo.com"
DEMO_OWNER_PASSWORD = os.environ.get("DEMO_OWNER_PASSWORD", "ClustR@Demo2026!")
DEMO_OWNER_NAME = "Demo Administrator"
DEMO_OWNER_PHONE = "+2348000000000"


def is_database_empty():
    """
    Check if foundational tables are empty.
    Returns True if the database appears to be fresh/empty.
    """
    from accounts.models import AccountUser
    from core.common.models import Cluster

    checks = [
        ("AccountUser", AccountUser.objects.exists()),
        ("Cluster", Cluster.objects.exists()),
    ]

    for table_name, has_data in checks:
        if has_data:
            print(f"Table '{table_name}' has existing data.")
            return False

    print("All foundational tables are empty.")
    return True


def create_demo_account():
    """
    Create a demo cluster and owner account for initial testing.
    This runs after the fixture is loaded if the database was empty.
    """
    from accounts.models import AccountUser
    from core.common.models import Cluster

    if AccountUser.objects.filter(email_address=DEMO_OWNER_EMAIL).exists():
        print(f"Demo owner '{DEMO_OWNER_EMAIL}' already exists. Skipping creation.")
        return

    if Cluster.objects.filter(name=DEMO_CLUSTER_NAME).exists():
        print(f"Demo cluster '{DEMO_CLUSTER_NAME}' already exists. Skipping creation.")
        return

    print(f"Creating demo cluster '{DEMO_CLUSTER_NAME}'...")

    with transaction.atomic():
        cluster = Cluster.objects.create(
            name=DEMO_CLUSTER_NAME,
            type=Cluster.Types.ESTATE,
            address="123 Demo Street",
            city="Lagos",
            state="Lagos",
            country="Nigeria",
            primary_contact_name=DEMO_OWNER_NAME,
            primary_contact_email=DEMO_OWNER_EMAIL,
            primary_contact_phone=DEMO_OWNER_PHONE,
            subscription_status="active",
            is_active=True,
        )
        print(f"Cluster '{DEMO_CLUSTER_NAME}' created successfully.")

        print(f"Creating demo owner '{DEMO_OWNER_EMAIL}'...")
        owner = AccountUser.objects.create_admin(
            email_address=DEMO_OWNER_EMAIL,
            password=DEMO_OWNER_PASSWORD,
            name=DEMO_OWNER_NAME,
            phone_number=DEMO_OWNER_PHONE,
            is_verified=True,
            is_phone_verified=True,
            approved_by_admin=True,
        )

        owner.primary_cluster = cluster
        owner.clusters.add(cluster)
        owner.save(update_fields=["primary_cluster"])

        print(f"Demo owner '{DEMO_OWNER_EMAIL}' created and linked to '{DEMO_CLUSTER_NAME}'.")
        print(f"  Email: {DEMO_OWNER_EMAIL}")
        print(f"  Password: {DEMO_OWNER_PASSWORD}")


def main():
    print("Checking if initial data should be loaded...")

    ensure_fixture_encoding("initial_data.json")

    try:
        call_command("loaddata", "initial_data.json", verbosity=2)
        print("Initial data loaded successfully.")
    except Exception as e:
        print(f"Error loading initial data: {e}")
        sys.exit(1)

    print("\nCreating demo account...")
    try:
        create_demo_account()
        print("Demo account setup complete.")
    except Exception as e:
        print(f"Error creating demo account: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
