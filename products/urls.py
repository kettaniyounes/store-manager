from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BrandViewSet, ProductViewSet, BarcodeCheckView



router = DefaultRouter() # Create a router instance
router.register(r'categories', CategoryViewSet, basename='category') # Register CategoryViewSet
router.register(r'brands', BrandViewSet, basename='brand') # Register BrandViewSet
router.register(r'products', ProductViewSet, basename='product') # Register ProductViewSet

urlpatterns = [
    path('', include(router.urls)), # Include router URLs
    path('check-barcode/', BarcodeCheckView.as_view(), name='check-barcode'),
]