from rest_framework.routers import DefaultRouter

from accounts.views.users import UserViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"", UserViewSet, basename="user")


urlpatterns = []

urlpatterns += router.urls
