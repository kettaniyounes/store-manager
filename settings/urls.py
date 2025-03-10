from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreSettingViewSet

router = DefaultRouter()
router.register(r'settings', StoreSettingViewSet, basename='store-setting') # StoreSettingViewSet

urlpatterns = [
    path('', include(router.urls)),
]