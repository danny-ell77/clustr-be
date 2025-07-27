#!/usr/bin/env python
import os
import subprocess
from typing import List


def initialize_django_apps(app_names: List[str], base_dir: str = None) -> None:
    """
    Initialize multiple Django apps and perform common setup tasks.

    Args:
        app_names: List of app names to create
        base_dir: Optional base directory path (defaults to current directory)
    """
    if base_dir:
        os.chdir(base_dir)

    for app_name in app_names:
        # Create the app
        print(f"Creating app: {app_name}")
        subprocess.run(["python", "manage.py", "startapp", app_name])

        # Create common directories
        dirs_to_create = [
            f"{app_name}/tests",
        ]

        for directory in dirs_to_create:
            os.makedirs(directory, exist_ok=True)

        # Create __init__.py files
        open(f"{app_name}/tests/__init__.py", "a").close()

        # Create urls.py
        with open(f"{app_name}/urls.py", "w") as f:
            f.write(
                """from django.urls import path
                from . import views

                app_name = '{}'

                urlpatterns = [
                    # Add your URL patterns here
                ]
                """.format(
                    app_name
                )
            )

        print(f"✓ {app_name} initialized with common directories and files")

    print("\nDon't forget to:")
    print("1. Add your apps to INSTALLED_APPS in settings.py")
    print("2. Include app URLs in your project's urls.py")
    print("3. Create your models in models.py")
    print("4. Run migrations if needed")


if __name__ == "__main__":
    # Example usage
    apps_to_create = ["accounts", "management", "members", "core"]

    initialize_django_apps(apps_to_create)
