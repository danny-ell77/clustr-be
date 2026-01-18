from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from accounts.models import (
    AccountUser,
    Role,
    UserVerification,
    PreviousPasswords,
    UserSettings,
    NotificationPreference,
    EmergencyContact,
)
from core.common.models import Cluster
from core.common.exceptions import ClusterAdminExistsException


@admin.register(AccountUser)
class AccountUserAdmin(BaseUserAdmin):
    ordering = ["email_address"]
    list_display = ["email_address", "name", "primary_cluster", "is_cluster_admin", "is_cluster_staff", "is_active"]
    search_fields = ["email_address", "name"]
    filter_horizontal = ["clusters"]
    list_filter = ["is_active", "is_staff", "is_superuser", "is_cluster_admin", "is_cluster_staff", "primary_cluster"]
    autocomplete_fields = ["primary_cluster"]
    change_form_template = "admin/accounts/accountuser/change_form.html"
    
    fieldsets = (
        (None, {"fields": ("email_address", "password")}),
        (_("Personal info"), {"fields": ("name", "phone_number", "profile_image_url")}),
        (
            _("Cluster Membership"),
            {
                "fields": (
                    "primary_cluster",
                    "clusters",
                ),
            },
        ),
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
                "fields": ("email_address", "name", "password1", "password2"),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/add-to-cluster/',
                self.admin_site.admin_view(self.add_to_cluster_view),
                name='accounts_accountuser_add_to_cluster',
            ),
        ]
        return custom_urls + urls

    def add_to_cluster_view(self, request, object_id):
        """View to add a single user to a cluster as admin or staff."""
        user = get_object_or_404(AccountUser, pk=object_id)
        
        if request.method == 'POST':
            cluster_id = request.POST.get('cluster')
            role_type = request.POST.get('role_type')
            
            if not cluster_id:
                messages.error(request, "Please select a cluster.")
                return HttpResponseRedirect(request.get_full_path())
            
            try:
                cluster = Cluster.objects.get(pk=cluster_id)
            except Cluster.DoesNotExist:
                messages.error(request, "Selected cluster does not exist.")
                return HttpResponseRedirect(request.get_full_path())
            
            if role_type == 'admin':
                try:
                    cluster.add_admin(user)
                    messages.success(request, f"Successfully added '{user.name}' to '{cluster.name}' as admin/owner.")
                except ClusterAdminExistsException as e:
                    messages.error(request, str(e.detail))
                    return HttpResponseRedirect(request.get_full_path())
            elif role_type == 'replace_admin':
                cluster.replace_admin(user)
                messages.success(request, f"Successfully replaced admin of '{cluster.name}' with '{user.name}'.")
            elif role_type == 'staff':
                cluster.add_staff(user)
                messages.success(request, f"Successfully added '{user.name}' to '{cluster.name}' as staff.")
            else:
                messages.error(request, "Invalid role type.")
                return HttpResponseRedirect(request.get_full_path())
            
            return redirect('admin:accounts_accountuser_change', object_id)
        
        clusters = Cluster.objects.filter(is_active=True).order_by('name')
        clusters_with_admin = []
        for cluster in clusters:
            admin = cluster.get_admin()
            cluster.has_admin = admin is not None
            cluster.admin_name = admin.name if admin else ''
            clusters_with_admin.append(cluster)
        
        return render(
            request,
            'admin/accounts/accountuser/add_to_cluster.html',
            {
                'title': f'Add {user.name} to Cluster',
                'user': user,
                'clusters': clusters_with_admin,
                'opts': self.model._meta,
            }
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['add_to_cluster_url'] = reverse(
            'admin:accounts_accountuser_add_to_cluster',
            args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context)


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
