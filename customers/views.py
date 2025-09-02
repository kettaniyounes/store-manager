# Django Import
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import (
    Customer, CustomerProfile, CustomerSegment, LoyaltyProgram, 
    CustomerLoyaltyAccount, LoyaltyTransaction, PromotionalCampaign
)
from .serializers import (
    CustomerSerializer, CustomerProfileSerializer, CustomerSegmentSerializer, 
    LoyaltyProgramSerializer, CustomerLoyaltyAccountSerializer, LoyaltyTransactionSerializer,
    PromotionalCampaignSerializer
)
from .permissions import IsSalesOrManagerOrReadOnly
from settings_app.base_viewsets import TenantAwareModelViewSet, SharedReferenceModelViewSet, TenantAwarePermission

# Python Import


class CustomerViewSet(TenantAwareModelViewSet):
    """ViewSet for managing customers with tenant isolation"""
    
    queryset = Customer.objects.all().order_by('name')
    serializer_class = CustomerSerializer
    permission_classes = [TenantAwarePermission, IsSalesOrManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['created_at', 'updated_at']
    search_fields = ['name', 'phone_number', 'email', 'address', 'notes']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Get customer profile with analytics"""
        customer = self.get_object()
        try:
            profile = customer.profile
            serializer = CustomerProfileSerializer(profile)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def update_analytics(self, request, pk=None):
        """Update customer analytics based on transaction history"""
        customer = self.get_object()
        try:
            profile, created = CustomerProfile.objects.get_or_create(customer=customer)
            profile.update_analytics()
            serializer = CustomerProfileSerializer(profile)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerProfileViewSet(TenantAwareModelViewSet):
    """ViewSet for managing customer profiles"""
    
    queryset = CustomerProfile.objects.all().order_by('-total_spent')
    serializer_class = CustomerProfileSerializer
    permission_classes = [TenantAwarePermission, IsSalesOrManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tier', 'is_vip', 'segment', 'marketing_opt_in']
    search_fields = ['customer__name', 'customer__email']
    ordering_fields = ['total_spent', 'total_orders', 'last_purchase_date']
    ordering = ['-total_spent']


class CustomerSegmentViewSet(SharedReferenceModelViewSet):
    """ViewSet for managing customer segments (shared across tenants)"""
    
    queryset = CustomerSegment.objects.all().order_by('name')
    serializer_class = CustomerSegmentSerializer
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['segment_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class LoyaltyProgramViewSet(SharedReferenceModelViewSet):
    """ViewSet for managing loyalty programs (shared across tenants)"""
    
    queryset = LoyaltyProgram.objects.all().order_by('name')
    serializer_class = LoyaltyProgramSerializer
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CustomerLoyaltyAccountViewSet(TenantAwareModelViewSet):
    """ViewSet for managing customer loyalty accounts"""
    
    queryset = CustomerLoyaltyAccount.objects.all().order_by('-current_points')
    serializer_class = CustomerLoyaltyAccountSerializer
    permission_classes = [TenantAwarePermission, IsSalesOrManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'is_active']
    search_fields = ['customer__name', 'customer__email']
    ordering_fields = ['current_points', 'enrollment_date', 'last_activity_date']
    ordering = ['-current_points']
    
    @action(detail=True, methods=['post'])
    def add_points(self, request, pk=None):
        """Add points to loyalty account"""
        account = self.get_object()
        points = request.data.get('points', 0)
        transaction_type = request.data.get('transaction_type', 'manual')
        description = request.data.get('description', '')
        
        if points <= 0:
            return Response({'error': 'Points must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            account.add_points(points, transaction_type, description=description)
            serializer = self.get_serializer(account)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def redeem_points(self, request, pk=None):
        """Redeem points from loyalty account"""
        account = self.get_object()
        points = request.data.get('points', 0)
        description = request.data.get('description', '')
        
        if points <= 0:
            return Response({'error': 'Points must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            account.redeem_points(points, description=description)
            serializer = self.get_serializer(account)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoyaltyTransactionViewSet(TenantAwareModelViewSet):
    """ViewSet for viewing loyalty transactions"""
    
    queryset = LoyaltyTransaction.objects.all().order_by('-transaction_date')
    serializer_class = LoyaltyTransactionSerializer
    permission_classes = [TenantAwarePermission, permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'loyalty_account']
    search_fields = ['loyalty_account__customer__name', 'description']
    ordering_fields = ['transaction_date', 'points_change']
    ordering = ['-transaction_date']
    
    # Override to make this read-only
    http_method_names = ['get', 'head', 'options']


class PromotionalCampaignViewSet(TenantAwareModelViewSet):
    """ViewSet for managing promotional campaigns"""
    
    queryset = PromotionalCampaign.objects.all().order_by('-start_date')
    serializer_class = PromotionalCampaignSerializer
    permission_classes = [TenantAwarePermission, IsSalesOrManagerOrReadOnly]
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['campaign_type', 'status', 'discount_type']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    @action(detail=False, methods=['get'])
    def active_campaigns(self, request):
        """Get currently active campaigns"""
        active_campaigns = self.get_queryset().filter(
            status='active',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        serializer = self.get_serializer(active_campaigns, many=True)
        return Response(serializer.data)