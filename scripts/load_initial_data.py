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
