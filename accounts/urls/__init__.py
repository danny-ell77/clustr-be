from django.urls import path, include

urlpatterns = [
    path('auth/', include('accounts.urls.auth')),
    path('users/', include('accounts.urls.users')),
    path('roles/', include('accounts.urls.roles')),
    path('user/', include('accounts.urls.user_settings')),
]