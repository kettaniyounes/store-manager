"""
URL configuration for store_management_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi, codecs
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static

import json
from decimal import Decimal


# Monkey-patch drf-yasg to use DRF's JSON encoder to handle Decimal serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# Instead of assigning codecs.json to a lambda,
# assign to its "dumps" attribute:
codecs.json.dumps = lambda obj, **kwargs: json.dumps(obj, cls=DecimalEncoder, **kwargs)


schema_view = get_schema_view(
   openapi.Info(
      title="Store Management API", # More descriptive title
      default_version='v1',
      description="""
      REST API for managing store operations: products, sales, customers, users, and settings.

      **Key Features:**

      - Product Management: Categories, Brands, Products, Inventory
      - Sales Management: Transactions, Payment Methods, Reporting
      - Customer Management
      - User Management with Roles and Permissions
      - Store Settings Configuration

      **Authentication:** JWT (JSON Web Token) based authentication is used for secure API access.

      **Rate Limiting:** API endpoints are rate-limited to protect against abuse.

      For detailed endpoint descriptions, request/response schemas, and authentication requirements, please refer to the endpoint documentation below.
      """, # More detailed API description
      terms_of_service="https://www.example.com/terms/", # Add your terms of service URL
      contact=openapi.Contact(email="support@yourstore.com", name="Store Management API Support"), # Add contact info
      license=openapi.License(name="BSD License"), # Add license info
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/products/', include('products.urls')), # Include products app URLs
    path('api/v1/sales/', include('sales.urls')),       # Include sales app URLs
    path('api/v1/customers/', include('customers.urls')), # Include customers app URLs
    path('api/v1/users/', include('users.urls')),       # Include users app URLs
    path('api/v1/settings/', include('settings_app.urls')),   # Include settings app URLs
    path('api/v1/suppliers/', include('suppliers.urls')), # Include suppliers app URLs
    path('api/v1/inventory/', include('inventory.urls')), # Include inventory app URLs
    path('api/v1/analytics/', include('analytics.urls')), # Include analytics app URLs
    path('api/v1/integrations/', include('integrations.urls')), # Include integrations app URLs

    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)