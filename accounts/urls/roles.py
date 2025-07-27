from rest_framework.routers import DefaultRouter

from accounts.views.roles import RoleViewSet

router = DefaultRouter(trailing_slash=True)

router.register(r"", RoleViewSet, basename="role")

urlpatterns = []

urlpatterns += router.urls
