from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from core.common.schema_generator import ClustRSchemaGenerator


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Simple health check endpoint for container orchestration."""
    return JsonResponse({"status": "ok"})


class PublicSchemaPermission(permissions.AllowAny):
    def has_permission(self, request, view):
        request.user = get_user_model()()  # empty user instance
        return True


schema_view = get_schema_view(
    openapi.Info(
        title="ClustR API",
        default_version="v1",
        description="ClustR's internal API documentation",
        terms_of_service="https://clustr-inc.com/terms-of-service/",
        contact=openapi.Contact(email="danielchibuezeolah@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[PublicSchemaPermission],
    generator_class=ClustRSchemaGenerator,
)

members = []

management = []


v1_endpoints = [
    path("auth/", include("accounts.urls.auth")),
    path("roles/", include("accounts.urls.roles")),
    path("accounts/", include("accounts.urls.users")),
    path("core/", include("core.common.urls")),
    path("members/", include("members.urls")),
    path("management/", include("management.urls")),
]


urlpatterns = [
    path("api/health/", health_check, name="health-check"),
    re_path("api/v1/", include(v1_endpoints)),
    path(
        "doc/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

# if settings.DEBUG:
#     if "debug_toolbar" in settings.INSTALLED_APPS:
#         import debug_toolbar
#
#         urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
