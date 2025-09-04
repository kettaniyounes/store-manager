"""
Tenant-specific authentication URLs.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Tenant-specific login
    path('login/', views.TenantLoginView.as_view(), name='tenant-login'),
    
    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # User profile management within tenant
    path('profile/', views.TenantUserProfileView.as_view(), name='tenant-profile'),
    
    # Change password within tenant context
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Logout
    path('logout/', views.LogoutView.as_view(), name='logout'),
]