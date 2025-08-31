
# Django Import
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import StoreSetting
from .serializers import StoreSettingSerializer
from .permissions import IsOwnerOrManagerReadOnlySetting


# Python Import

class StoreSettingViewSet(viewsets.ModelViewSet):
    queryset = StoreSetting.objects.all().order_by('key') # Order settings by key
    serializer_class = StoreSettingSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Default permission - refine
    permission_classes = [IsOwnerOrManagerReadOnlySetting] # Use IsOwnerOrManagerReadOnlySetting permission

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Filter backends
    filterset_fields = ['data_type', 'created_at', 'updated_at', 'key'] # Filter fields
    search_fields = ['key', 'value', 'description'] # Search fields
    ordering_fields = ['key', 'created_at'] # Ordering fields
    ordering = ['key'] # Default ordering