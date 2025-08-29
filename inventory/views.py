from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import timedelta

from .models import LocationInventory, StoreTransfer, PhysicalCount
from .serializers import (
    LocationInventorySerializer, StoreTransferSerializer, 
    PhysicalCountSerializer, InventoryReportSerializer,
    LowStockReportSerializer, TransferReportSerializer
)
from .permissions import InventoryPermission
from settings_app.models import Store


class LocationInventoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inventory levels at specific store locations.
    Provides CRUD operations and specialized inventory management actions.
    """
    queryset = LocationInventory.objects.all()
    serializer_class = LocationInventorySerializer
    permission_classes = [IsAuthenticated, InventoryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'product', 'product__category']
    search_fields = ['product__name', 'product__sku', 'store__name']
    ordering_fields = ['quantity', 'reserved_quantity', 'last_updated']
    ordering = ['-last_updated']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores if not superuser
        if not self.request.user.is_superuser:
            user_stores = Store.objects.filter(
                Q(managers=self.request.user) | Q(staff=self.request.user)
            ).distinct()
            queryset = queryset.filter(store__in=user_stores)
        return queryset

    @action(detail=False, methods=['get'])
    def low_stock_report(self, request):
        """Get products with low stock across all locations"""
        low_stock_items = self.get_queryset().filter(
            quantity__lte=F('product__low_stock_threshold')
        ).select_related('product', 'store')
        
        serializer = LowStockReportSerializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def reorder_report(self, request):
        """Get products that need reordering based on reorder points"""
        reorder_items = self.get_queryset().filter(
            quantity__lte=F('product__reorder_point')
        ).select_related('product', 'store')
        
        serializer = LowStockReportSerializer(reorder_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def inventory_summary(self, request):
        """Get inventory summary by store"""
        store_id = request.query_params.get('store_id')
        queryset = self.get_queryset()
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        summary = queryset.aggregate(
            total_products=Sum('quantity'),
            total_reserved=Sum('reserved_quantity'),
            available_stock=Sum(F('quantity') - F('reserved_quantity')),
            low_stock_count=Sum(
                1, filter=Q(quantity__lte=F('product__low_stock_threshold'))
            )
        )
        
        return Response(summary)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust stock quantity for a specific location inventory"""
        inventory = self.get_object()
        adjustment_quantity = request.data.get('adjustment_quantity', 0)
        reason = request.data.get('reason', 'Manual adjustment')
        
        if not adjustment_quantity:
            return Response(
                {'error': 'adjustment_quantity is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update inventory quantity
        inventory.quantity += adjustment_quantity
        inventory.save()
        
        # Create stock movement record (assuming we have this in products app)
        # This would need to be imported from products.models
        
        return Response({
            'message': 'Stock adjusted successfully',
            'new_quantity': inventory.quantity,
            'adjustment': adjustment_quantity
        })


class StoreTransferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transfers between store locations.
    Handles stock movement between different stores.
    """
    queryset = StoreTransfer.objects.all()
    serializer_class = StoreTransferSerializer
    permission_classes = [IsAuthenticated, InventoryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['from_store', 'to_store', 'status', 'product']
    search_fields = ['product__name', 'product__sku', 'transfer_number']
    ordering_fields = ['created_at', 'transfer_date', 'quantity']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores
        if not self.request.user.is_superuser:
            user_stores = Store.objects.filter(
                Q(managers=self.request.user) | Q(staff=self.request.user)
            ).distinct()
            queryset = queryset.filter(
                Q(from_store__in=user_stores) | Q(to_store__in=user_stores)
            )
        return queryset

    @action(detail=True, methods=['post'])
    def approve_transfer(self, request, pk=None):
        """Approve a pending transfer"""
        transfer = self.get_object()
        
        if transfer.status != 'pending':
            return Response(
                {'error': 'Transfer is not in pending status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if source store has enough stock
        try:
            from_inventory = LocationInventory.objects.get(
                store=transfer.from_store, 
                product=transfer.product
            )
            if from_inventory.quantity < transfer.quantity:
                return Response(
                    {'error': 'Insufficient stock in source store'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LocationInventory.DoesNotExist:
            return Response(
                {'error': 'Product not found in source store'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the transfer
        transfer.status = 'approved'
        transfer.approved_by = request.user
        transfer.approved_at = timezone.now()
        transfer.save()
        
        return Response({'message': 'Transfer approved successfully'})

    @action(detail=True, methods=['post'])
    def complete_transfer(self, request, pk=None):
        """Complete an approved transfer by updating inventory levels"""
        transfer = self.get_object()
        
        if transfer.status != 'approved':
            return Response(
                {'error': 'Transfer must be approved before completion'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update source store inventory
            from_inventory = LocationInventory.objects.get(
                store=transfer.from_store, 
                product=transfer.product
            )
            from_inventory.quantity -= transfer.quantity
            from_inventory.save()
            
            # Update destination store inventory
            to_inventory, created = LocationInventory.objects.get_or_create(
                store=transfer.to_store,
                product=transfer.product,
                defaults={'quantity': 0}
            )
            to_inventory.quantity += transfer.quantity
            to_inventory.save()
            
            # Mark transfer as completed
            transfer.status = 'completed'
            transfer.completed_at = timezone.now()
            transfer.save()
            
            return Response({'message': 'Transfer completed successfully'})
            
        except LocationInventory.DoesNotExist:
            return Response(
                {'error': 'Inventory record not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def transfer_report(self, request):
        """Get transfer report with filtering options"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        store_id = request.query_params.get('store_id')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        if store_id:
            queryset = queryset.filter(
                Q(from_store_id=store_id) | Q(to_store_id=store_id)
            )
        
        serializer = TransferReportSerializer(queryset, many=True)
        return Response(serializer.data)


class PhysicalCountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing physical inventory counts.
    Handles periodic inventory audits and adjustments.
    """
    queryset = PhysicalCount.objects.all()
    serializer_class = PhysicalCountSerializer
    permission_classes = [IsAuthenticated, InventoryPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'status', 'counted_by']
    search_fields = ['store__name', 'notes']
    ordering_fields = ['count_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by user's accessible stores
        if not self.request.user.is_superuser:
            user_stores = Store.objects.filter(
                Q(managers=self.request.user) | Q(staff=self.request.user)
            ).distinct()
            queryset = queryset.filter(store__in=user_stores)
        return queryset

    @action(detail=True, methods=['post'])
    def finalize_count(self, request, pk=None):
        """Finalize physical count and update inventory levels"""
        physical_count = self.get_object()
        
        if physical_count.status != 'in_progress':
            return Response(
                {'error': 'Count is not in progress'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update inventory levels based on physical count
        adjustments_made = 0
        for item in physical_count.physicalcountitem_set.all():
            try:
                inventory = LocationInventory.objects.get(
                    store=physical_count.store,
                    product=item.product
                )
                
                if inventory.quantity != item.counted_quantity:
                    # Record the adjustment
                    adjustment = item.counted_quantity - inventory.quantity
                    inventory.quantity = item.counted_quantity
                    inventory.save()
                    adjustments_made += 1
                    
            except LocationInventory.DoesNotExist:
                # Create new inventory record if it doesn't exist
                LocationInventory.objects.create(
                    store=physical_count.store,
                    product=item.product,
                    quantity=item.counted_quantity
                )
                adjustments_made += 1
        
        # Mark count as completed
        physical_count.status = 'completed'
        physical_count.completed_at = timezone.now()
        physical_count.save()
        
        return Response({
            'message': 'Physical count finalized successfully',
            'adjustments_made': adjustments_made
        })

    @action(detail=False, methods=['get'])
    def count_summary(self, request):
        """Get summary of physical counts"""
        store_id = request.query_params.get('store_id')
        queryset = self.get_queryset()
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        # Get counts from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_counts = queryset.filter(created_at__gte=thirty_days_ago)
        
        summary = {
            'total_counts': queryset.count(),
            'recent_counts': recent_counts.count(),
            'pending_counts': queryset.filter(status='in_progress').count(),
            'completed_counts': queryset.filter(status='completed').count(),
        }
        
        return Response(summary)