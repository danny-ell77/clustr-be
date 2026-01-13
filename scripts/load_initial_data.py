#!/usr/bin/env python
"""
Load initial data fixture into a fresh database.

This script flushes the database, loads the initial_data.json fixture using
Django's standard loaddata command, and creates a demo account.
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_production")

import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from django.db import transaction


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

SUPERUSER_EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL", "superadmin@clustr.com")
SUPERUSER_PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "ClustR@Super2026!")
SUPERUSER_NAME = os.environ.get("DJANGO_SUPERUSER_NAME", "Super Admin")


def create_superuser():
    """
    Create a Django superuser for admin access.
    Credentials can be set via environment variables:
    - DJANGO_SUPERUSER_EMAIL
    - DJANGO_SUPERUSER_PASSWORD
    - DJANGO_SUPERUSER_NAME
    """
    from accounts.models import AccountUser

    if AccountUser.objects.filter(email_address=SUPERUSER_EMAIL).exists():
        print(f"Superuser '{SUPERUSER_EMAIL}' already exists. Skipping creation.")
        return

    print(f"Creating superuser '{SUPERUSER_EMAIL}'...")
    AccountUser.objects.create_superuser(
        email_address=SUPERUSER_EMAIL,
        password=SUPERUSER_PASSWORD,
        name=SUPERUSER_NAME,
    )
    print(f"Superuser created successfully.")
    print(f"  Email: {SUPERUSER_EMAIL}")
    print(f"  Password: {SUPERUSER_PASSWORD}")


def create_demo_account():
    """
    Create a demo cluster and owner account for initial testing.
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
    print("=" * 60)
    print("INITIAL DATA LOADER")
    print("=" * 60)

    print("\n[Step 1/5] Checking fixture encoding...")
    ensure_fixture_encoding("initial_data.json")

    print("\n[Step 2/5] Flushing database (removing all existing data)...")
    try:
        call_command("flush", "--no-input", verbosity=1)
        print("Database flushed successfully.")
    except Exception as e:
        print(f"Error flushing database: {e}")
        sys.exit(1)

    print("\n[Step 3/5] Loading initial_data.json fixture...")
    try:
        call_command("loaddata", "initial_data.json", verbosity=2)
        print("Fixture loaded successfully.")
    except Exception as e:
        print(f"Error loading fixture: {e}")
        sys.exit(1)

    print("\n[Step 4/5] Creating superuser for admin access...")
    try:
        create_superuser()
    except Exception as e:
        print(f"Error creating superuser: {e}")
        sys.exit(1)

    print("\n[Step 5/5] Creating demo account...")
    try:
        create_demo_account()
        print("Demo account setup complete.")
    except Exception as e:
        print(f"Error creating demo account: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("INITIAL DATA LOAD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
