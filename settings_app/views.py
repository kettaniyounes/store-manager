# Django Import
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta

from .models import StoreSetting, Store, StoreTransfer, StoreTransferItem
from .serializers import (
    StoreSettingSerializer, StoreSerializer, StoreTransferSerializer, 
    StoreTransferItemSerializer, StorePerformanceSerializer, StoreComparisonSerializer
)
from .permissions import IsOwnerOrManagerReadOnlySetting


# Python Import

class StoreViewSet(viewsets.ModelViewSet):
    """ViewSet for managing store locations"""
    
    queryset = Store.objects.all().order_by('name')
    serializer_class = StoreSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store_type', 'is_active', 'is_main_store', 'manager']
    search_fields = ['name', 'code', 'city', 'state_province']
    ordering_fields = ['name', 'code', 'created_at', 'store_type']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores if not superuser
        if not self.request.user.is_superuser:
            # Users can see stores they manage or are assigned to
            queryset = queryset.filter(
                Q(manager=self.request.user.pk)
            ).distinct()
        return queryset
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get performance metrics for a specific store"""
        store = self.get_object()
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        end_date = timezone.now().date()
        
        # Get sales data
        from sales.models import SaleTransaction
        sales_data = SaleTransaction.objects.filter(
            store=store,
            sale_date__date__range=[start_date, end_date],
            status='completed'
        ).aggregate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id'),
            average_transaction_value=Avg('total_amount'),
            total_profit=Sum('gross_profit')
        )
        
        # Get inventory data
        from inventory.models import LocationInventory
        inventory_data = LocationInventory.objects.filter(store=store).aggregate(
            inventory_value=Sum(F('quantity_on_hand') * F('average_cost')),
            low_stock_items=Count('id', filter=Q(quantity_on_hand__lte=F('reorder_point')))
        )
        
        # Calculate profit margin
        profit_margin = 0
        if sales_data['total_sales'] and sales_data['total_sales'] > 0:
            profit_margin = (sales_data['total_profit'] / sales_data['total_sales']) * 100
        
        performance_data = {
            'store_id': store.id,
            'store_name': store.name,
            'store_code': store.code,
            'total_sales': sales_data['total_sales'] or 0,
            'total_transactions': sales_data['total_transactions'] or 0,
            'average_transaction_value': sales_data['average_transaction_value'] or 0,
            'total_profit': sales_data['total_profit'] or 0,
            'profit_margin': profit_margin,
            'inventory_value': inventory_data['inventory_value'] or 0,
            'low_stock_items': inventory_data['low_stock_items'] or 0,
            'period_start': start_date,
            'period_end': end_date,
        }
        
        serializer = StorePerformanceSerializer(performance_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """Compare performance across all stores"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        end_date = timezone.now().date()
        
        stores_performance = []
        total_company_sales = 0
        total_company_profit = 0
        best_store = None
        best_sales = 0
        
        for store in self.get_queryset():
            # Get performance data for each store
            from sales.models import SaleTransaction
            sales_data = SaleTransaction.objects.filter(
                store=store,
                sale_date__date__range=[start_date, end_date],
                status='completed'
            ).aggregate(
                total_sales=Sum('total_amount'),
                total_transactions=Count('id'),
                average_transaction_value=Avg('total_amount'),
                total_profit=Sum('gross_profit')
            )
            
            from inventory.models import LocationInventory
            inventory_data = LocationInventory.objects.filter(store=store).aggregate(
                inventory_value=Sum(F('quantity_on_hand') * F('average_cost')),
                low_stock_items=Count('id', filter=Q(quantity_on_hand__lte=F('reorder_point')))
            )
            
            store_sales = sales_data['total_sales'] or 0
            store_profit = sales_data['total_profit'] or 0
            
            profit_margin = 0
            if store_sales > 0:
                profit_margin = (store_profit / store_sales) * 100
            
            store_performance = {
                'store_id': store.id,
                'store_name': store.name,
                'store_code': store.code,
                'total_sales': store_sales,
                'total_transactions': sales_data['total_transactions'] or 0,
                'average_transaction_value': sales_data['average_transaction_value'] or 0,
                'total_profit': store_profit,
                'profit_margin': profit_margin,
                'inventory_value': inventory_data['inventory_value'] or 0,
                'low_stock_items': inventory_data['low_stock_items'] or 0,
                'period_start': start_date,
                'period_end': end_date,
            }
            
            stores_performance.append(store_performance)
            total_company_sales += store_sales
            total_company_profit += store_profit
            
            if store_sales > best_sales:
                best_sales = store_sales
                best_store = store.name
        
        comparison_data = {
            'stores': stores_performance,
            'total_company_sales': total_company_sales,
            'total_company_profit': total_company_profit,
            'best_performing_store': best_store or 'N/A',
            'period_start': start_date,
            'period_end': end_date,
        }
        
        serializer = StoreComparisonSerializer(comparison_data)
        return Response(serializer.data)


class StoreTransferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing store transfers"""
    
    queryset = StoreTransfer.objects.all().order_by('-request_date')
    serializer_class = StoreTransferSerializer
    permission_classes = [IsOwnerOrManagerReadOnlySetting]
    authentication_classes = [JWTAuthentication]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['from_store', 'to_store', 'status', 'requested_by']
    search_fields = ['transfer_number', 'notes']
    ordering_fields = ['request_date', 'shipped_date', 'received_date']
    ordering = ['-request_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores
        if not self.request.user.is_superuser:
            user_stores = Store.objects.filter(
                Q(manager=self.request.user.pk)
            ).distinct()
            queryset = queryset.filter(
                Q(from_store__in=user_stores)
            )
        return queryset
    
    def perform_create(self, serializer):
        """Set the requesting user when creating a transfer"""
        serializer.save(requested_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending transfer"""
        transfer = self.get_object()
        
        if transfer.status != 'pending':
            return Response(
                {'error': 'Transfer is not in pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transfer.status = 'in_transit'
        transfer.approved_by = request.user
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        """Mark transfer as shipped"""
        transfer = self.get_object()
        
        if transfer.status != 'in_transit':
            return Response(
                {'error': 'Transfer must be approved before shipping'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transfer.shipped_by = request.user
        transfer.shipped_date = timezone.now()
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Mark transfer as received and update inventory"""
        transfer = self.get_object()
        
        if not transfer.shipped_date:
            return Response(
                {'error': 'Transfer must be shipped before receiving'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update inventory levels
        from inventory.models import LocationInventory
        
        for item in transfer.transfer_items.all():
            # Reduce inventory at source store
            try:
                from_inventory = LocationInventory.objects.get(
                    store=transfer.from_store,
                    product=item.product,
                    product_variant=item.product_variant
                )
                from_inventory.quantity_on_hand -= item.quantity_shipped
                from_inventory.save()
            except LocationInventory.DoesNotExist:
                pass
            
            # Increase inventory at destination store
            to_inventory, created = LocationInventory.objects.get_or_create(
                store=transfer.to_store,
                product=item.product,
                product_variant=item.product_variant,
                defaults={'quantity_on_hand': 0}
            )
            to_inventory.quantity_on_hand += item.quantity_received or item.quantity_shipped
            to_inventory.save()
        
        transfer.status = 'completed'
        transfer.received_by = request.user
        transfer.received_date = timezone.now()
        transfer.save()
        
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)


class StoreSettingViewSet(viewsets.ModelViewSet):
    queryset = StoreSetting.objects.all().order_by('store', 'key') # Order settings by store and key
    serializer_class = StoreSettingSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Default permission - refine
    permission_classes = [IsOwnerOrManagerReadOnlySetting] # Use IsOwnerOrManagerReadOnlySetting permission
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] # Filter backends
    filterset_fields = ['store', 'data_type', 'created_at', 'updated_at', 'key'] # Filter fields
    search_fields = ['key', 'value', 'description'] # Search fields
    ordering_fields = ['key', 'created_at'] # Ordering fields
    ordering = ['store', 'key'] # Default ordering
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores
        if not self.request.user.is_superuser:
            user_stores = Store.objects.filter(
                Q(manager=self.request.user.pk)
            ).distinct()
            queryset = queryset.filter(
                Q(store__in=user_stores) | Q(store__isnull=True)  # Include global settings
            )
        return queryset