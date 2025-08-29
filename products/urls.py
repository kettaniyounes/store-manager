from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, BrandViewSet, ProductImageViewSet, ProductVariantViewSet, 
    ProductViewSet, BarcodeCheckView, StockMovementViewSet, StockAdjustmentViewSet,
    ProductExpirationViewSet
)



router = DefaultRouter() # Create a router instance
router.register(r'categories', CategoryViewSet, basename='category') # Register CategoryViewSet
router.register(r'brands', BrandViewSet, basename='brand') # Register BrandViewSet
router.register(r'products', ProductViewSet, basename='product') # Register ProductViewSet
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
router.register(r'stock-adjustments', StockAdjustmentViewSet, basename='stock-adjustment')
router.register(r'product-expirations', ProductExpirationViewSet, basename='product-expiration')

product_router = DefaultRouter() # Create a NEW router instance for nested routes
product_router.register(r'images', ProductImageViewSet, basename='product-images') # Register ProductImageViewSet under 'images'
product_router.register(r'variants', ProductVariantViewSet, basename='product-variants') # Register ProductVariantViewSet under 'variants'

urlpatterns = [
    path('', include(router.urls)), # Include router URLs
    path('<int:product_pk>/', include(product_router.urls)), # Include nested product_router URLs under products/{product_pk}/
    path('check-barcode/', BarcodeCheckView.as_view(), name='check-barcode'),
]