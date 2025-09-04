"""
Tenant-specific URL configuration for multi-tenant architecture.
These URLs are accessible within tenant context and handle store operations.
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
      title="Store Management API - Tenant",
      default_version='v1',
      description="""
      Tenant-specific API endpoints for store management operations.

      **Key Features:**
      - Product Management: Categories, Brands, Products, Inventory
      - Sales Management: Transactions, Payment Methods, Reporting
      - Customer Management
      - User Management with Roles and Permissions
      - Store Settings Configuration
      - Analytics and Reporting
      - Supplier Management
      - Inventory Tracking
      - Third-party Integrations

      **Authentication:** JWT (JSON Web Token) based authentication with tenant context.
      **Rate Limiting:** API endpoints are rate-limited to protect against abuse.
      """,
      contact=openapi.Contact(email="support@yourstore.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Tenant-specific admin interface
    path('admin/', admin.site.urls),
    
    # Store management endpoints (tenant-specific)
    path('api/v1/products/', include('products.urls')),
    path('api/v1/sales/', include('sales.urls')),
    path('api/v1/customers/', include('customers.urls')),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/settings/', include('settings_app.urls')),
    path('api/v1/suppliers/', include('suppliers.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    
    # Tenant-specific authentication
    path('api/v1/auth/', include('tenants.tenant_auth_urls')),
    
    # API documentation for tenant
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)