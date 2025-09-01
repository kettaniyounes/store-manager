# Django Import
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Dashboard, KPIMetric, MetricSnapshot, TrendAnalysis, 
    Alert, AlertInstance, ComparativeAnalysis
)
from .serializers import (
    DashboardSerializer, KPIMetricSerializer, MetricSnapshotSerializer,
    TrendAnalysisSerializer, AlertSerializer, AlertInstanceSerializer,
    ComparativeAnalysisSerializer, RealTimeMetricsSerializer,
    PerformanceComparisonSerializer
)
from settings_app.permissions import IsOwnerOrManagerReadOnlySetting

# Python Import


class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing analytics dashboards"""
    
    queryset = Dashboard.objects.all().order_by('dashboard_type', 'name')
    serializer_class = DashboardSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dashboard_type', 'is_public', 'is_default', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'dashboard_type', 'created_at']
    ordering = ['dashboard_type', 'name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Users can see their own dashboards and public dashboards
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(owner=self.request.user.pk) | Q(is_public=True)
            )
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone an existing dashboard"""
        original_dashboard = self.get_object()
        
        # Create a copy with new name
        cloned_dashboard = Dashboard.objects.create(
            name=f"{original_dashboard.name} (Copy)",
            dashboard_type=original_dashboard.dashboard_type,
            description=original_dashboard.description,
            owner=request.user,
            is_public=False,
            is_default=False,
            layout_config=original_dashboard.layout_config,
            refresh_interval=original_dashboard.refresh_interval
        )
        
        serializer = self.get_serializer(cloned_dashboard)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def real_time_metrics(self, request):
        """Get real-time metrics for dashboard"""
        today = timezone.now().date()
        
        # Get sales data for today
        from sales.models import SaleTransaction
        today_sales = SaleTransaction.objects.filter(
            sale_date__date=today,
            status='completed'
        )
        
        total_revenue = today_sales.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_transactions = today_sales.count()
        
        avg_transaction = today_sales.aggregate(
            avg=Avg('total_amount')
        )['avg'] or 0
        
        # Get top selling product today
        from products.models import Product
        top_product = today_sales.values(
            'sale_items__product__name'
        ).annotate(
            total_qty=Sum('sale_items__quantity')
        ).order_by('-total_qty').first()
        
        top_selling_product = top_product['sale_items__product__name'] if top_product else 'N/A'
        
        # Get low stock alerts
        low_stock_count = Product.objects.filter(
            stock_quantity__lte=F('low_stock_threshold'),
            is_active=True
        ).count()
        
        # Get active customers (customers who made purchases in last 30 days)
        from customers.models import Customer
        active_customers = Customer.objects.filter(
            sale_transactions__sale_date__gte=timezone.now() - timedelta(days=30)
        ).distinct().count()
        
        # Calculate profit margin
        total_profit = today_sales.aggregate(
            total=Sum('gross_profit')
        )['total'] or 0
        
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        # Get inventory value
        inventory_value = Product.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum(F('stock_quantity') * F('average_cost'))
        )['total'] or 0
        
        metrics_data = {
            'total_revenue_today': total_revenue,
            'total_transactions_today': total_transactions,
            'average_transaction_value': avg_transaction,
            'top_selling_product': top_selling_product,
            'low_stock_alerts': low_stock_count,
            'active_customers': active_customers,
            'profit_margin_today': profit_margin,
            'sales_vs_target': 85.5,  # This would be calculated based on targets
            'inventory_value': inventory_value,
            'pending_orders': 0,  # This would come from purchase orders
            'last_updated': timezone.now()
        }
        
        serializer = RealTimeMetricsSerializer(metrics_data)
        return Response(serializer.data)


class KPIMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for managing KPI metrics"""
    
    queryset = KPIMetric.objects.all().order_by('metric_type', 'name')
    serializer_class = KPIMetricSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['metric_type', 'calculation_method', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'metric_type', 'created_at']
    ordering = ['metric_type', 'name']
    
    @action(detail=True, methods=['post'])
    def calculate_current_value(self, request, pk=None):
        """Calculate and store current value for a KPI metric"""
        metric = self.get_object()
        # TODO
        # This would contain the logic to calculate the metric value
        # based on the metric's configuration
        # For now, we'll return a placeholder
        
        current_value = self._calculate_metric_value(metric)
        
        # Create a new snapshot
        snapshot = MetricSnapshot.objects.create(
            metric=metric,
            value=current_value,
            period_start=timezone.now() - timedelta(days=1),
            period_end=timezone.now(),
            metadata={'calculation_method': 'real_time'}
        )
        
        return Response({
            'metric_id': metric.id,
            'current_value': current_value,
            'snapshot_id': snapshot.id,
            'calculated_at': timezone.now()
        })
    
    def _calculate_metric_value(self, metric):
        """Helper method to calculate metric value based on configuration"""
        # This is a simplified implementation
        # In a real system, this would use the metric's configuration
        # to query the appropriate models and calculate the value
        
        if metric.metric_type == 'revenue':
            from sales.models import SaleTransaction
            return SaleTransaction.objects.filter(
                status='completed',
                sale_date__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        elif metric.metric_type == 'sales_volume':
            from sales.models import SaleTransaction
            return SaleTransaction.objects.filter(
                status='completed',
                sale_date__gte=timezone.now() - timedelta(days=30)
            ).count()
        
        # Add more metric calculations as needed
        return 0


class MetricSnapshotViewSet(viewsets.ModelViewSet):
    """ViewSet for managing metric snapshots"""
    
    queryset = MetricSnapshot.objects.all().order_by('-snapshot_date')
    serializer_class = MetricSnapshotSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['metric', 'store', 'snapshot_date']
    ordering_fields = ['snapshot_date', 'value']
    ordering = ['-snapshot_date']
    
    @action(detail=False, methods=['get'])
    def time_series(self, request):
        """Get time series data for metrics"""
        metric_id = request.query_params.get('metric_id')
        store_id = request.query_params.get('store_id')
        days = int(request.query_params.get('days', 30))
        
        queryset = self.get_queryset()
        
        if metric_id:
            queryset = queryset.filter(metric_id=metric_id)
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(snapshot_date__gte=start_date)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TrendAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for managing trend analysis"""
    
    queryset = TrendAnalysis.objects.all().order_by('-analysis_date')
    serializer_class = TrendAnalysisSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['metric', 'store', 'trend_type', 'trend_direction']
    ordering_fields = ['analysis_date', 'trend_strength', 'forecast_accuracy']
    ordering = ['-analysis_date']
    
    @action(detail=True, methods=['post'])
    def regenerate_forecast(self, request, pk=None):
        """Regenerate forecast for a trend analysis"""
        trend_analysis = self.get_object()
        
        # This would contain the logic to regenerate the forecast
        # using the specified forecast method
        
        # For now, we'll update the analysis date and return success
        trend_analysis.analysis_date = timezone.now()
        trend_analysis.next_analysis_date = timezone.now() + timedelta(days=7)
        trend_analysis.save()
        
        serializer = self.get_serializer(trend_analysis)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet for managing analytics alerts"""
    
    queryset = Alert.objects.all().order_by('severity', 'name')
    serializer_class = AlertSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'metric', 'store', 'severity', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'severity', 'last_triggered', 'trigger_count']
    ordering = ['severity', 'name']
    
    @action(detail=True, methods=['post'])
    def test_alert(self, request, pk=None):
        """Test an alert by manually triggering it"""
        alert = self.get_object()
        
        # Create a test alert instance
        test_instance = AlertInstance.objects.create(
            alert=alert,
            triggered_value=0,
            message=f"Test alert triggered by {request.user.username}"
        )
        
        return Response({
            'message': 'Alert test triggered successfully',
            'instance_id': test_instance.id,
            'triggered_at': test_instance.triggered_at
        })


class AlertInstanceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing alert instances"""
    
    queryset = AlertInstance.objects.all().order_by('-triggered_at')
    serializer_class = AlertInstanceSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert', 'is_acknowledged', 'acknowledged_by']
    ordering_fields = ['triggered_at', 'acknowledged_at']
    ordering = ['-triggered_at']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert instance"""
        instance = self.get_object()
        
        instance.is_acknowledged = True
        instance.acknowledged_by = request.user
        instance.acknowledged_at = timezone.now()
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unacknowledged(self, request):
        """Get all unacknowledged alerts"""
        unacknowledged = self.get_queryset().filter(is_acknowledged=False)
        serializer = self.get_serializer(unacknowledged, many=True)
        return Response(serializer.data)


class ComparativeAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for managing comparative analysis"""
    
    queryset = ComparativeAnalysis.objects.all().order_by('-analysis_date')
    serializer_class = ComparativeAnalysisSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['comparison_type', 'created_by']
    search_fields = ['name', 'insights']
    ordering_fields = ['name', 'analysis_date']
    ordering = ['-analysis_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def store_performance_comparison(self, request):
        """Compare performance across all stores"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        from settings_app.models import Store
        from sales.models import SaleTransaction
        
        store_comparisons = []
        best_performer = None
        worst_performer = None
        best_sales = 0
        worst_sales = float('inf')
        total_company_sales = 0
        
        for store in Store.objects.filter(is_active=True):
            sales_data = SaleTransaction.objects.filter(
                store=store,
                sale_date__date__gte=start_date,
                status='completed'
            ).aggregate(
                total_sales=Sum('total_amount'),
                total_transactions=Count('id'),
                total_profit=Sum('gross_profit')
            )
            
            store_sales = sales_data['total_sales'] or 0
            store_profit = sales_data['total_profit'] or 0
            
            profit_margin = (store_profit / store_sales * 100) if store_sales > 0 else 0
            
            store_data = {
                'store_id': store.id,
                'store_name': store.name,
                'store_code': store.code,
                'total_sales': store_sales,
                'total_transactions': sales_data['total_transactions'] or 0,
                'total_profit': store_profit,
                'profit_margin': profit_margin,
                'sales_per_day': store_sales / days if days > 0 else 0
            }
            
            store_comparisons.append(store_data)
            total_company_sales += store_sales
            
            if store_sales > best_sales:
                best_sales = store_sales
                best_performer = store.name
            
            if store_sales < worst_sales:
                worst_sales = store_sales
                worst_performer = store.name
        
        comparison_data = {
            'store_comparisons': store_comparisons,
            'best_performer': best_performer or 'N/A',
            'worst_performer': worst_performer or 'N/A',
            'company_average': total_company_sales / len(store_comparisons) if store_comparisons else 0,
            'total_stores': len(store_comparisons),
            'comparison_period': f"Last {days} days"
        }
        
        serializer = PerformanceComparisonSerializer(comparison_data)
        return Response(serializer.data)