"""
Public schema URL configuration for multi-tenant architecture.
These URLs are accessible without tenant context and handle tenant management.
"""

from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
   openapi.Info(
      title="Store Management API - Public",
      default_version='v1',
      description="""
      Public API endpoints for tenant management and user registration.
      
      **Public Features:**
      - Tenant Registration and Management
      - User Authentication (Login/Register)
      - Domain Management
      - Public Documentation
      
      **Note:** These endpoints are available without tenant context.
      """,
      contact=openapi.Contact(email="support@yourstore.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin interface for public schema
    path('admin/', admin.site.urls),
    
    # Tenant management endpoints
    path('api/v1/tenants/', include('tenants.urls')),
    
    # Public authentication endpoints
    path('api/v1/auth/', include('tenants.auth_urls')),
    
    # API documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)