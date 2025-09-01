from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid
import json

class WebhookEndpoint(models.Model):
    """Model for managing webhook endpoints"""
    
    EVENT_CHOICES = [
        ('sale.created', 'Sale Created'),
        ('sale.updated', 'Sale Updated'),
        ('sale.completed', 'Sale Completed'),
        ('product.created', 'Product Created'),
        ('product.updated', 'Product Updated'),
        ('inventory.low_stock', 'Low Stock Alert'),
        ('customer.created', 'Customer Created'),
        ('transfer.completed', 'Store Transfer Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    url = models.URLField()
    events = models.JSONField(default=list, help_text="List of events to subscribe to")
    is_active = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Retry configuration
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=60, help_text="Delay in seconds between retries")
    
    class Meta:
        db_table = 'webhook_endpoints'
        verbose_name = 'Webhook Endpoint'
        verbose_name_plural = 'Webhook Endpoints'
    
    def __str__(self):
        return f"{self.name} - {self.url}"

class WebhookDelivery(models.Model):
    """Model for tracking webhook delivery attempts"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempt_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'webhook_deliveries'
        verbose_name = 'Webhook Delivery'
        verbose_name_plural = 'Webhook Deliveries'
        ordering = ['-created_at']

class APIKey(models.Model):
    """Model for managing API keys for third-party integrations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=list, help_text="List of allowed permissions")
    rate_limit = models.IntegerField(default=1000, help_text="Requests per hour")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def __str__(self):
        return f"{self.name} - {self.key[:8]}..."

class BulkOperation(models.Model):
    """Model for tracking bulk operations"""
    
    OPERATION_CHOICES = [
        ('import', 'Import'),
        ('export', 'Export'),
        ('update', 'Bulk Update'),
        ('delete', 'Bulk Delete'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation_type = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    model_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Progress tracking
    total_records = models.IntegerField(default=0)
    processed_records = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    
    # File references
    input_file = models.FileField(upload_to='bulk_operations/input/', null=True, blank=True)
    output_file = models.FileField(upload_to='bulk_operations/output/', null=True, blank=True)
    error_file = models.FileField(upload_to='bulk_operations/errors/', null=True, blank=True)
    
    # Configuration and results
    configuration = models.JSONField(default=dict)
    results = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'bulk_operations'
        verbose_name = 'Bulk Operation'
        verbose_name_plural = 'Bulk Operations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operation_type.title()} {self.model_name} - {self.status}"
    
    @property
    def progress_percentage(self):
        if self.total_records == 0:
            return 0
        return (self.processed_records / self.total_records) * 100

class ExternalIntegration(models.Model):
    """Model for managing external service integrations"""
    
    SERVICE_CHOICES = [
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('quickbooks', 'QuickBooks'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('mailchimp', 'MailChimp'),
        ('slack', 'Slack'),
        ('zapier', 'Zapier'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict)
    credentials = models.JSONField(default=dict)  # Encrypted in production
    sync_settings = models.JSONField(default=dict)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'external_integrations'
        verbose_name = 'External Integration'
        verbose_name_plural = 'External Integrations'
    
    def __str__(self):
        return f"{self.name} ({self.service_type})"