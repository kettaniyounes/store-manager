from rest_framework import serializers
from .models import WebhookEndpoint, WebhookDelivery, APIKey, BulkOperation, ExternalIntegration

class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = ['id', 'name', 'url', 'events', 'is_active', 'max_retries', 'retry_delay', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source='endpoint.name', read_only=True)
    
    class Meta:
        model = WebhookDelivery
        fields = ['id', 'endpoint', 'endpoint_name', 'event_type', 'status', 'response_status', 
                 'attempt_count', 'created_at', 'delivered_at', 'next_retry_at']
        read_only_fields = ['id', 'created_at', 'delivered_at']

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key', 'is_active', 'permissions', 'rate_limit', 
                 'created_at', 'last_used_at', 'expires_at']
        read_only_fields = ['id', 'key', 'created_at', 'last_used_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Generate API key
        import secrets
        validated_data['key'] = f"sk_{secrets.token_urlsafe(32)}"
        return super().create(validated_data)

class BulkOperationSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = BulkOperation
        fields = ['id', 'operation_type', 'model_name', 'status', 'total_records', 
                 'processed_records', 'successful_records', 'failed_records', 
                 'progress_percentage', 'input_file', 'output_file', 'error_file',
                 'created_at', 'started_at', 'completed_at', 'error_message']
        read_only_fields = ['id', 'status', 'processed_records', 'successful_records', 
                           'failed_records', 'progress_percentage', 'output_file', 
                           'error_file', 'created_at', 'started_at', 'completed_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class ExternalIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalIntegration
        fields = ['id', 'name', 'service_type', 'is_active', 'configuration', 
                 'sync_settings', 'last_sync_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'last_sync_at', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)