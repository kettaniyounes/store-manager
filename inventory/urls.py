from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'location-inventory', views.LocationInventoryViewSet)
router.register(r'store-transfers', views.StoreTransferViewSet)
router.register(r'physical-counts', views.PhysicalCountViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
]