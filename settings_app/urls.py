from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreSettingViewSet, StoreViewSet, StoreTransferViewSet

router = DefaultRouter()
router.register(r'settings', StoreSettingViewSet, basename='store-setting') # StoreSettingViewSet
router.register(r'stores', StoreViewSet, basename='store') # StoreViewSet for store management
router.register(r'transfers', StoreTransferViewSet, basename='store-transfer') # StoreTransferViewSet for inter-store transfers

urlpatterns = [
    path('', include(router.urls)),
]