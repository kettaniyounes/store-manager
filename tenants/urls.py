"""
URL patterns for tenant management in public schema.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.TenantViewSet, basename='tenant')
router.register(r'users', views.TenantUserViewSet, basename='tenant-user')
router.register(r'invitations', views.TenantInvitationViewSet, basename='tenant-invitation')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.TenantRegistrationView.as_view(), name='tenant-register'),
    path('<uuid:tenant_id>/users/', views.TenantUserListView.as_view(), name='tenant-users'),
    path('domains/', views.DomainManagementView.as_view(), name='domain-management'),
]