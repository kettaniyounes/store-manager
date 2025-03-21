from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, SupplierProductViewSet, PurchaseOrderViewSet, PurchaseOrderItemViewSet  # Import your ViewSets

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')          # /api/v1/suppliers/
router.register(r'supplier-products', SupplierProductViewSet, basename='supplier-product') # /api/v1/supplier-products/
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')    # /api/v1/purchase-orders/
router.register(r'purchase-order-items', PurchaseOrderItemViewSet, basename='purchase-order-item') # /api/v1/purchase-order-items/ (Optional - consider if you need this direct endpoint)

urlpatterns = [
    path('', include(router.urls)),
]