from django.urls import path
from rest_framework_simplejwt.views import token_refresh

from accounts.views.auth import (
    ClusterMemberRegistrationAPIView,
    ClusterRegistrationAPIView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    SigninView,
    check_token_status,
)

urlpatterns = [
    path("signin/", SigninView.as_view(), name="login"),
    path(
        "signin/refresh/",
        token_refresh,
        name="token_refresh",
    ),
    path(
        "cluster-signup/", ClusterRegistrationAPIView.as_view(), name="register_cluster"
    ),
    path(
        "member-signup/",
        ClusterMemberRegistrationAPIView.as_view(),
        name="register_member",
    ),
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="reset_password"),
    path("token-status/", check_token_status, name="check_token_status"),
]
