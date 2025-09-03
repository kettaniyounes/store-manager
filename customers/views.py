# Django Import
from rest_framework import viewsets, permissions, filters 
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend # Import DjangoFilterBackend
from .models import Customer
from .serializers import CustomerSerializer
from .permissions import IsSalesOrManagerOrReadOnly

# Python Import

class CustomerViewSet(viewsets.ModelViewSet):
    
    queryset = Customer.objects.all().order_by('name') # Order customers by name
    serializer_class = CustomerSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Default permission - refine
    permission_classes = [IsSalesOrManagerOrReadOnly] # Use IsSalesStaffOrReadOnly permission
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Filter backends
    filterset_fields = ['created_at', 'updated_at'] # Example filter fields (can add more if needed)
    search_fields = ['name', 'phone_number', 'email', 'address', 'notes'] # Search fields
    ordering_fields = ['name', 'created_at'] # Ordering fields
    ordering = ['name'] # Default ordering