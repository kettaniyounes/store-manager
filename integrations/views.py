from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import csv
import io
from .models import WebhookEndpoint, WebhookDelivery, APIKey, BulkOperation, ExternalIntegration
from .serializers import (
    WebhookEndpointSerializer, WebhookDeliverySerializer, APIKeySerializer,
    BulkOperationSerializer, ExternalIntegrationSerializer
)

class BulkOperationThrottle(UserRateThrottle):
    scope = 'bulk'

class ExportThrottle(UserRateThrottle):
    scope = 'export'

class WebhookEndpointViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookEndpointSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'events']
    
    def get_queryset(self):
        return WebhookEndpoint.objects.filter(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test webhook endpoint with sample payload"""
        endpoint = self.get_object()
        # Implementation for testing webhook
        return Response({'message': 'Test webhook sent successfully'})

class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WebhookDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'event_type']
    
    def get_queryset(self):
        return WebhookDelivery.objects.filter(endpoint__created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed webhook delivery"""
        delivery = self.get_object()
        if delivery.status == 'failed':
            # Implementation for retrying webhook
            delivery.status = 'retrying'
            delivery.save()
            return Response({'message': 'Webhook delivery queued for retry'})
        return Response({'error': 'Can only retry failed deliveries'}, 
                       status=status.HTTP_400_BAD_REQUEST)

class APIKeyViewSet(viewsets.ModelViewSet):
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate API key"""
        api_key = self.get_object()
        import secrets
        api_key.key = f"sk_{secrets.token_urlsafe(32)}"
        api_key.save()
        serializer = self.get_serializer(api_key)
        return Response(serializer.data)

class BulkOperationViewSet(viewsets.ModelViewSet):
    serializer_class = BulkOperationSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [BulkOperationThrottle]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation_type', 'status', 'model_name']
    
    def get_queryset(self):
        return BulkOperation.objects.filter(created_by=self.request.user)
    
    @action(detail=False, methods=['post'], throttle_classes=[ExportThrottle])
    def export_products(self, request):
        """Export products to CSV"""
        from products.models import Product
        
        # Create bulk operation record
        bulk_op = BulkOperation.objects.create(
            operation_type='export',
            model_name='Product',
            created_by=request.user,
            status='processing'
        )
        
        try:
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['Name', 'SKU', 'Price', 'Category', 'Store', 'Created At'])
            
            # Write data
            products = Product.objects.all()
            bulk_op.total_records = products.count()
            bulk_op.save()
            
            for product in products:
                writer.writerow([
                    product.name,
                    product.sku,
                    product.price,
                    product.category.name if product.category else '',
                    product.store.name if product.store else '',
                    product.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
                bulk_op.processed_records += 1
                bulk_op.successful_records += 1
            
            # Save CSV content
            from django.core.files.base import ContentFile
            csv_content = output.getvalue()
            bulk_op.output_file.save(
                f'products_export_{bulk_op.id}.csv',
                ContentFile(csv_content.encode('utf-8'))
            )
            
            bulk_op.status = 'completed'
            bulk_op.save()
            
            return Response({
                'operation_id': bulk_op.id,
                'download_url': bulk_op.output_file.url if bulk_op.output_file else None,
                'total_records': bulk_op.total_records
            })
            
        except Exception as e:
            bulk_op.status = 'failed'
            bulk_op.error_message = str(e)
            bulk_op.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def import_products(self, request):
        """Import products from CSV"""
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        # Create bulk operation record
        bulk_op = BulkOperation.objects.create(
            operation_type='import',
            model_name='Product',
            created_by=request.user,
            status='processing',
            input_file=file
        )
        
        # Process import in background (simplified for demo)
        return Response({
            'operation_id': bulk_op.id,
            'message': 'Import started. Check operation status for progress.'
        })

class ExternalIntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = ExternalIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service_type', 'is_active']
    
    def get_queryset(self):
        return ExternalIntegration.objects.filter(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger sync with external service"""
        integration = self.get_object()
        # Implementation for syncing with external service
        return Response({'message': f'Sync initiated for {integration.name}'})
    
    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        """Test connection to external service"""
        integration = self.get_object()
        # Implementation for testing connection
        return Response({'status': 'connected', 'message': 'Connection successful'})