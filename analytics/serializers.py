# Django Import
from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    Dashboard, KPIMetric, MetricSnapshot, TrendAnalysis, 
    Alert, AlertInstance, ComparativeAnalysis
)

# Python Import


class DashboardSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'dashboard_type', 'description', 'owner', 'owner_name',
            'is_public', 'is_default', 'layout_config', 'refresh_interval',
            'widget_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_widget_count(self, obj):
        """Get number of widgets in the dashboard"""
        return len(obj.layout_config.get('widgets', []))


class KPIMetricSerializer(serializers.ModelSerializer):
    current_value = serializers.SerializerMethodField()
    target_achievement = serializers.SerializerMethodField()
    
    class Meta:
        model = KPIMetric
        fields = [
            'id', 'name', 'metric_type', 'description', 'calculation_method',
            'source_model', 'source_field', 'filter_conditions', 'custom_query',
            'unit', 'target_value', 'current_value', 'target_achievement',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_value(self, obj):
        """Get the most recent metric value"""
        latest_snapshot = obj.snapshots.order_by('-snapshot_date').first()
        return latest_snapshot.value if latest_snapshot else None
    
    def get_target_achievement(self, obj):
        """Calculate target achievement percentage"""
        current_value = self.get_current_value(obj)
        if current_value and obj.target_value:
            return (current_value / obj.target_value) * 100
        return None


class MetricSnapshotSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    metric_unit = serializers.CharField(source='metric.unit', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.code', read_only=True)
    
    class Meta:
        model = MetricSnapshot
        fields = [
            'id', 'metric', 'metric_name', 'metric_unit', 'store', 'store_name', 'store_code',
            'value', 'period_start', 'period_end', 'snapshot_date', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrendAnalysisSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    forecast_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = TrendAnalysis
        fields = [
            'id', 'metric', 'metric_name', 'store', 'store_name', 'trend_type',
            'forecast_method', 'analysis_period_days', 'forecast_period_days',
            'trend_direction', 'trend_strength', 'forecast_accuracy',
            'forecast_data', 'forecast_summary', 'analysis_date', 'next_analysis_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_forecast_summary(self, obj):
        """Get summary of forecast data"""
        forecast_data = obj.forecast_data
        if not forecast_data or 'forecast_values' not in forecast_data:
            return None
        
        values = forecast_data['forecast_values']
        if not values:
            return None
        
        return {
            'min_forecast': min(values),
            'max_forecast': max(values),
            'avg_forecast': sum(values) / len(values),
            'forecast_points': len(values)
        }


class AlertSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    recipient_count = serializers.SerializerMethodField()
    recent_instances = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'name', 'alert_type', 'metric', 'metric_name', 'store', 'store_name',
            'condition', 'severity', 'recipients', 'recipient_count', 'is_active',
            'last_triggered', 'trigger_count', 'recent_instances',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_triggered', 'trigger_count', 'created_at', 'updated_at']
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()
    
    def get_recent_instances(self, obj):
        """Get recent alert instances"""
        recent = obj.instances.order_by('-triggered_at')[:5]
        return AlertInstanceSerializer(recent, many=True).data


class AlertInstanceSerializer(serializers.ModelSerializer):
    alert_name = serializers.CharField(source='alert.name', read_only=True)
    alert_severity = serializers.CharField(source='alert.severity', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.username', read_only=True)
    
    class Meta:
        model = AlertInstance
        fields = [
            'id', 'alert', 'alert_name', 'alert_severity', 'triggered_value',
            'message', 'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'triggered_at'
        ]
        read_only_fields = ['id', 'triggered_at']


class ComparativeAnalysisSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    metric_names = serializers.SerializerMethodField()
    
    class Meta:
        model = ComparativeAnalysis
        fields = [
            'id', 'name', 'comparison_type', 'metrics', 'metric_names',
            'comparison_config', 'results', 'insights', 'created_by', 'created_by_name',
            'analysis_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_metric_names(self, obj):
        return [metric.name for metric in obj.metrics.all()]


class RealTimeMetricsSerializer(serializers.Serializer):
    """Serializer for real-time dashboard metrics"""
    
    total_revenue_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions_today = serializers.IntegerField()
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_selling_product = serializers.CharField()
    low_stock_alerts = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    profit_margin_today = serializers.DecimalField(max_digits=5, decimal_places=2)
    sales_vs_target = serializers.DecimalField(max_digits=5, decimal_places=2)
    inventory_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_orders = serializers.IntegerField()
    last_updated = serializers.DateTimeField()


class PerformanceComparisonSerializer(serializers.Serializer):
    """Serializer for store performance comparison"""
    
    store_comparisons = serializers.ListField(
        child=serializers.DictField()
    )
    best_performer = serializers.CharField()
    worst_performer = serializers.CharField()
    company_average = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_stores = serializers.IntegerField()
    comparison_period = serializers.CharField()