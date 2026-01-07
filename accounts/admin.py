from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from accounts.models import (
    AccountUser,
    Role,
    UserVerification,
    PreviousPasswords,
    UserSettings,
    NotificationPreference,
    EmergencyContact,
)

@admin.register(AccountUser)
class AccountUserAdmin(BaseUserAdmin):
    ordering = ["email_address"]
    list_display = ["email_address", "name", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email_address", "name"]
    filter_horizontal = [] 
    list_filter = ["is_active", "is_staff", "is_superuser"]
    
    # Since we set username = None in the model, we need to adjust fieldsets
    # Using default fieldsets but replacing username with email_address where appropriate
    # or defining custom fieldsets. For now, let's try to keep it simple.
    
    fieldsets = (
        (None, {"fields": ("email_address", "password")}),
        (_("Personal info"), {"fields": ("name", "phone_number", "profile_image_url")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_owner",
                    "is_cluster_admin",
                    "is_cluster_staff",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_("Verification"), {"fields": ("is_verified", "is_phone_verified", "approved_by_admin")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email_address", "name", "password"),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name"]
    list_filter = ["created_at"]


@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = ["requested_by", "notification_event", "is_used", "requested_at"]
    list_filter = ["is_used", "notification_event", "requested_at"]
    search_fields = ["requested_by__email_address"]


@admin.register(PreviousPasswords)
class PreviousPasswordsAdmin(admin.ModelAdmin):
    list_display = ["user", "last_modified_at"]
    search_fields = ["user__email_address"]


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ["user"]
    search_fields = ["user__email_address"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user"]
    search_fields = ["user__email_address"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "relationship", "contact_type", "is_primary"]
    list_filter = ["contact_type", "is_primary"]
    search_fields = ["name", "user__email_address", "phone_number"]
