# Django Imports
from django.db import models
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError

# Python Imports
from decimal import Decimal
import json
from datetime import datetime, timedelta


class Dashboard(models.Model):
    """Model for customizable analytics dashboards"""
    
    DASHBOARD_TYPES = [
        ('executive', 'Executive Dashboard'),
        ('sales', 'Sales Dashboard'),
        ('inventory', 'Inventory Dashboard'),
        ('financial', 'Financial Dashboard'),
        ('store_performance', 'Store Performance Dashboard'),
        ('custom', 'Custom Dashboard'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Dashboard Name'
    )
    dashboard_type = models.CharField(
        max_length=20,
        choices=DASHBOARD_TYPES,
        verbose_name='Dashboard Type'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_dashboards',
        verbose_name='Dashboard Owner'
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name='Is Public',
        help_text='Whether this dashboard is visible to all users'
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name='Is Default',
        help_text='Whether this is the default dashboard for its type'
    )
    layout_config = models.JSONField(
        default=dict,
        verbose_name='Layout Configuration',
        help_text='JSON configuration for dashboard layout and widgets'
    )
    refresh_interval = models.IntegerField(
        default=300,
        verbose_name='Refresh Interval (seconds)',
        help_text='How often dashboard data should refresh'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Dashboard'
        verbose_name_plural = 'Dashboards'
        ordering = ['dashboard_type', 'name']
        indexes = [
            models.Index(fields=['dashboard_type', 'is_public'], name='dashboard_type_public_idx'),
            models.Index(fields=['owner', 'dashboard_type'], name='dashboard_owner_type_idx'),
        ]

    def clean(self):
        # Ensure only one default dashboard per type per user
        if self.is_default:
            existing_default = Dashboard.objects.filter(
                dashboard_type=self.dashboard_type,
                owner=self.owner,
                is_default=True
            ).exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError(f"A default {self.get_dashboard_type_display()} already exists for this user.")

    def __str__(self):
        return f"{self.name} ({self.get_dashboard_type_display()})"


class KPIMetric(models.Model):
    """Model for Key Performance Indicator definitions"""
    
    METRIC_TYPES = [
        ('revenue', 'Revenue'),
        ('profit', 'Profit'),
        ('sales_volume', 'Sales Volume'),
        ('customer_count', 'Customer Count'),
        ('inventory_turnover', 'Inventory Turnover'),
        ('average_transaction', 'Average Transaction Value'),
        ('conversion_rate', 'Conversion Rate'),
        ('growth_rate', 'Growth Rate'),
        ('margin', 'Profit Margin'),
        ('custom', 'Custom Metric'),
    ]
    
    CALCULATION_METHODS = [
        ('sum', 'Sum'),
        ('average', 'Average'),
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        ('ratio', 'Ratio'),
        ('custom_query', 'Custom Query'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Metric Name'
    )
    metric_type = models.CharField(
        max_length=20,
        choices=METRIC_TYPES,
        verbose_name='Metric Type'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=CALCULATION_METHODS,
        verbose_name='Calculation Method'
    )
    source_model = models.CharField(
        max_length=100,
        verbose_name='Source Model',
        help_text='Django model to query for this metric'
    )
    source_field = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Source Field',
        help_text='Field to aggregate (if applicable)'
    )
    filter_conditions = models.JSONField(
        default=dict,
        verbose_name='Filter Conditions',
        help_text='JSON object with filter conditions for the query'
    )
    custom_query = models.TextField(
        blank=True,
        verbose_name='Custom Query',
        help_text='Custom SQL query for complex metrics'
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Unit',
        help_text='Unit of measurement (e.g., $, %, units)'
    )
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Target Value',
        help_text='Target value for this KPI'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'KPI Metric'
        verbose_name_plural = 'KPI Metrics'
        ordering = ['metric_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_metric_type_display()})"


class MetricSnapshot(models.Model):
    """Model for storing historical metric values"""
    
    metric = models.ForeignKey(
        KPIMetric,
        on_delete=models.CASCADE,
        related_name='snapshots',
        verbose_name='KPI Metric'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metric_snapshots',
        verbose_name='Store',
        help_text='Store this metric applies to (null for company-wide)'
    )
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Metric Value'
    )
    period_start = models.DateTimeField(
        verbose_name='Period Start'
    )
    period_end = models.DateTimeField(
        verbose_name='Period End'
    )
    snapshot_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Snapshot Date'
    )
    metadata = models.JSONField(
        default=dict,
        verbose_name='Metadata',
        help_text='Additional data about this metric snapshot'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Metric Snapshot'
        verbose_name_plural = 'Metric Snapshots'
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['metric', 'snapshot_date'], name='metric_snapshot_date_idx'),
            models.Index(fields=['store', 'snapshot_date'], name='store_snapshot_date_idx'),
            models.Index(fields=['period_start', 'period_end'], name='snapshot_period_idx'),
        ]

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"{self.metric.name}: {self.value}{store_info} ({self.snapshot_date.date()})"


class TrendAnalysis(models.Model):
    """Model for trend analysis and forecasting"""
    
    TREND_TYPES = [
        ('linear', 'Linear Trend'),
        ('exponential', 'Exponential Trend'),
        ('seasonal', 'Seasonal Trend'),
        ('cyclical', 'Cyclical Trend'),
    ]
    
    FORECAST_METHODS = [
        ('linear_regression', 'Linear Regression'),
        ('moving_average', 'Moving Average'),
        ('exponential_smoothing', 'Exponential Smoothing'),
        ('seasonal_decomposition', 'Seasonal Decomposition'),
    ]
    
    metric = models.ForeignKey(
        KPIMetric,
        on_delete=models.CASCADE,
        related_name='trend_analyses',
        verbose_name='KPI Metric'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='trend_analyses',
        verbose_name='Store'
    )
    trend_type = models.CharField(
        max_length=20,
        choices=TREND_TYPES,
        verbose_name='Trend Type'
    )
    forecast_method = models.CharField(
        max_length=30,
        choices=FORECAST_METHODS,
        verbose_name='Forecast Method'
    )
    analysis_period_days = models.IntegerField(
        default=90,
        verbose_name='Analysis Period (Days)',
        help_text='Number of days of historical data to analyze'
    )
    forecast_period_days = models.IntegerField(
        default=30,
        verbose_name='Forecast Period (Days)',
        help_text='Number of days to forecast into the future'
    )
    trend_direction = models.CharField(
        max_length=20,
        choices=[
            ('increasing', 'Increasing'),
            ('decreasing', 'Decreasing'),
            ('stable', 'Stable'),
            ('volatile', 'Volatile'),
        ],
        verbose_name='Trend Direction'
    )
    trend_strength = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Trend Strength',
        help_text='Strength of the trend (0-100)'
    )
    forecast_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Forecast Accuracy (%)',
        help_text='Accuracy of previous forecasts'
    )
    forecast_data = models.JSONField(
        default=dict,
        verbose_name='Forecast Data',
        help_text='JSON object containing forecast values and confidence intervals'
    )
    analysis_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Analysis Date'
    )
    next_analysis_date = models.DateTimeField(
        verbose_name='Next Analysis Date'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Trend Analysis'
        verbose_name_plural = 'Trend Analyses'
        ordering = ['-analysis_date']
        indexes = [
            models.Index(fields=['metric', 'analysis_date'], name='trend_metric_date_idx'),
            models.Index(fields=['store', 'analysis_date'], name='trend_store_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.next_analysis_date:
            # Schedule next analysis in 7 days by default
            self.next_analysis_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"{self.metric.name} Trend Analysis{store_info} ({self.analysis_date.date()})"


class Alert(models.Model):
    """Model for analytics alerts and notifications"""
    
    ALERT_TYPES = [
        ('threshold', 'Threshold Alert'),
        ('trend', 'Trend Alert'),
        ('anomaly', 'Anomaly Detection'),
        ('forecast', 'Forecast Alert'),
        ('comparison', 'Comparison Alert'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Alert Name'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name='Alert Type'
    )
    metric = models.ForeignKey(
        KPIMetric,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='KPI Metric'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name='Store'
    )
    condition = models.JSONField(
        verbose_name='Alert Condition',
        help_text='JSON object defining when this alert should trigger'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium',
        verbose_name='Severity Level'
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='analytics_alerts',
        verbose_name='Alert Recipients'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    last_triggered = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Triggered'
    )
    trigger_count = models.IntegerField(
        default=0,
        verbose_name='Trigger Count'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Analytics Alert'
        verbose_name_plural = 'Analytics Alerts'
        ordering = ['severity', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_severity_display()})"


class AlertInstance(models.Model):
    """Model for individual alert occurrences"""
    
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='instances',
        verbose_name='Alert'
    )
    triggered_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Triggered Value'
    )
    message = models.TextField(
        verbose_name='Alert Message'
    )
    is_acknowledged = models.BooleanField(
        default=False,
        verbose_name='Is Acknowledged'
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name='Acknowledged By'
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Acknowledged At'
    )
    triggered_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Triggered At'
    )

    class Meta:
        verbose_name = 'Alert Instance'
        verbose_name_plural = 'Alert Instances'
        ordering = ['-triggered_at']

    def __str__(self):
        return f"{self.alert.name} - {self.triggered_at.strftime('%Y-%m-%d %H:%M')}"


class ComparativeAnalysis(models.Model):
    """Model for comparative analytics between stores, periods, etc."""
    
    COMPARISON_TYPES = [
        ('store_vs_store', 'Store vs Store'),
        ('period_vs_period', 'Period vs Period'),
        ('actual_vs_target', 'Actual vs Target'),
        ('actual_vs_forecast', 'Actual vs Forecast'),
        ('category_comparison', 'Category Comparison'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Analysis Name'
    )
    comparison_type = models.CharField(
        max_length=20,
        choices=COMPARISON_TYPES,
        verbose_name='Comparison Type'
    )
    metrics = models.ManyToManyField(
        KPIMetric,
        related_name='comparative_analyses',
        verbose_name='Metrics to Compare'
    )
    comparison_config = models.JSONField(
        verbose_name='Comparison Configuration',
        help_text='JSON configuration for the comparison parameters'
    )
    results = models.JSONField(
        default=dict,
        verbose_name='Analysis Results',
        help_text='JSON object containing comparison results and insights'
    )
    insights = models.TextField(
        blank=True,
        verbose_name='Key Insights',
        help_text='Automatically generated insights from the analysis'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comparative_analyses',
        verbose_name='Created By'
    )
    analysis_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Analysis Date'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Comparative Analysis'
        verbose_name_plural = 'Comparative Analyses'
        ordering = ['-analysis_date']

    def __str__(self):
        return f"{self.name} ({self.get_comparison_type_display()})"