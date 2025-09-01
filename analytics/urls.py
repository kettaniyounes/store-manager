from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardViewSet, KPIMetricViewSet, MetricSnapshotViewSet,
    TrendAnalysisViewSet, AlertViewSet, AlertInstanceViewSet,
    ComparativeAnalysisViewSet
)

router = DefaultRouter()
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'metrics', KPIMetricViewSet, basename='kpi-metric')
router.register(r'snapshots', MetricSnapshotViewSet, basename='metric-snapshot')
router.register(r'trends', TrendAnalysisViewSet, basename='trend-analysis')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'alert-instances', AlertInstanceViewSet, basename='alert-instance')
router.register(r'comparisons', ComparativeAnalysisViewSet, basename='comparative-analysis')

urlpatterns = [
    path('', include(router.urls)),
]