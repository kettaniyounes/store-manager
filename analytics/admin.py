from django.contrib import admin
from .models import (
    Dashboard, KPIMetric, MetricSnapshot, TrendAnalysis,
    Alert, AlertInstance, ComparativeAnalysis
)


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'dashboard_type', 'owner', 'is_public', 'is_default', 'created_at']
    list_filter = ['dashboard_type', 'is_public', 'is_default', 'created_at']
    search_fields = ['name', 'description', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'dashboard_type', 'description', 'owner')
        }),
        ('Configuration', {
            'fields': ('is_public', 'is_default', 'refresh_interval', 'layout_config')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(KPIMetric)
class KPIMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'metric_type', 'calculation_method', 'unit', 'target_value', 'is_active']
    list_filter = ['metric_type', 'calculation_method', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'metric_type', 'description', 'unit', 'target_value')
        }),
        ('Calculation Configuration', {
            'fields': ('calculation_method', 'source_model', 'source_field', 'filter_conditions', 'custom_query')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ['metric', 'store', 'value', 'snapshot_date']
    list_filter = ['metric', 'store', 'snapshot_date']
    search_fields = ['metric__name', 'store__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'snapshot_date'


@admin.register(TrendAnalysis)
class TrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ['metric', 'store', 'trend_type', 'trend_direction', 'trend_strength', 'analysis_date']
    list_filter = ['trend_type', 'trend_direction', 'forecast_method', 'analysis_date']
    search_fields = ['metric__name', 'store__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'analysis_date'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['name', 'alert_type', 'metric', 'store', 'severity', 'is_active', 'trigger_count']
    list_filter = ['alert_type', 'severity', 'is_active', 'created_at']
    search_fields = ['name', 'metric__name', 'store__name']
    readonly_fields = ['last_triggered', 'trigger_count', 'created_at', 'updated_at']
    filter_horizontal = ['recipients']


@admin.register(AlertInstance)
class AlertInstanceAdmin(admin.ModelAdmin):
    list_display = ['alert', 'triggered_value', 'is_acknowledged', 'acknowledged_by', 'triggered_at']
    list_filter = ['is_acknowledged', 'triggered_at', 'alert__severity']
    search_fields = ['alert__name', 'message', 'acknowledged_by__username']
    readonly_fields = ['triggered_at']
    date_hierarchy = 'triggered_at'


@admin.register(ComparativeAnalysis)
class ComparativeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['name', 'comparison_type', 'created_by', 'analysis_date']
    list_filter = ['comparison_type', 'analysis_date', 'created_by']
    search_fields = ['name', 'insights', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['metrics']
    date_hierarchy = 'analysis_date'