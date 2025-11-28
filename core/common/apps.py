"""
Django app configuration for core.common.
"""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """
    Configuration for the core.common app.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.common"
    
    def ready(self):
        """
        Initialize the app when Django starts.
        
        This method is called when the app is ready. It's a good place to
        perform initialization tasks like configuring logging.
        """
        ...