from django.contrib import admin
from .models import WebhookEndpoint, WebhookDelivery, APIKey, BulkOperation, ExternalIntegration

@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'events', 'created_at']
    search_fields = ['name', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'event_type', 'status', 'attempt_count', 'created_at']
    list_filter = ['status', 'event_type', 'created_at']
    search_fields = ['endpoint__name', 'event_type']
    readonly_fields = ['id', 'created_at', 'delivered_at']

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'rate_limit', 'created_at', 'last_used_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['id', 'key', 'created_at', 'last_used_at']

@admin.register(BulkOperation)
class BulkOperationAdmin(admin.ModelAdmin):
    list_display = ['operation_type', 'model_name', 'status', 'progress_percentage', 'created_by', 'created_at']
    list_filter = ['operation_type', 'status', 'model_name', 'created_at']
    search_fields = ['created_by__username', 'model_name']
    readonly_fields = ['id', 'progress_percentage', 'created_at', 'started_at', 'completed_at']

@admin.register(ExternalIntegration)
class ExternalIntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'is_active', 'created_by', 'last_sync_at']
    list_filter = ['service_type', 'is_active', 'created_at']
    search_fields = ['name', 'service_type']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_sync_at']