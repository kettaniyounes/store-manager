"""
Public authentication URLs for tenant registration and login.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Public registration (creates tenant + user)
    path('register/', views.PublicRegistrationView.as_view(), name='public-register'),
    
    # Public login (tenant-aware)
    path('login/', views.TenantAwareLoginView.as_view(), name='public-login'),
    
    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Password reset
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]