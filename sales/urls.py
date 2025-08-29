from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentMethodViewSet, SaleTransactionViewSet, FinancialPeriodViewSet,
    ProfitLossReportViewSet, SalesAnalyticsViewSet, TaxReportViewSet
)

router = DefaultRouter()
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method') # PaymentMethodViewSet
router.register(r'transactions', SaleTransactionViewSet, basename='sale-transaction') # SaleTransactionViewSet
router.register(r'financial-periods', FinancialPeriodViewSet, basename='financial-period')
router.register(r'profit-loss-reports', ProfitLossReportViewSet, basename='profit-loss-report')
router.register(r'sales-analytics', SalesAnalyticsViewSet, basename='sales-analytics')
router.register(r'tax-reports', TaxReportViewSet, basename='tax-report')

urlpatterns = [
    path('', include(router.urls)),
]