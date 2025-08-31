
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentMethodViewSet, SaleTransactionViewSet

router = DefaultRouter()
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method') # PaymentMethodViewSet
router.register(r'transactions', SaleTransactionViewSet, basename='sale-transaction') # SaleTransactionViewSet

urlpatterns = [
    path('', include(router.urls)),
]