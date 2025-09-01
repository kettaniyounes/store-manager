from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WebhookEndpointViewSet, WebhookDeliveryViewSet, APIKeyViewSet,
    BulkOperationViewSet, ExternalIntegrationViewSet
)

router = DefaultRouter()
router.register(r'webhooks', WebhookEndpointViewSet, basename='webhook')
router.register(r'webhook-deliveries', WebhookDeliveryViewSet, basename='webhook-delivery')
router.register(r'api-keys', APIKeyViewSet, basename='api-key')
router.register(r'bulk-operations', BulkOperationViewSet, basename='bulk-operation')
router.register(r'external-integrations', ExternalIntegrationViewSet, basename='external-integration')

urlpatterns = [
    path('', include(router.urls)),
]