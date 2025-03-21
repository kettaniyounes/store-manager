
# Django Import
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from django.db.models import F
from django.db import transaction
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.permissions import IsInventoryStaffOrReadOnly
from .models import Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderItem
from .serializers import SupplierSerializer, SupplierProductSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer
from .permissions import IsManagerOrReadOnlySupplier, IsPurchasingManagerOrStaffOrCreatePO, IsManagerOrOwnerSupplier  # Import permission classes
from products.models import Product

# Python Import


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on Supplier model.
    Requires Manager or Owner role for write operations, read-only for others.
    """
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    permission_classes = [IsManagerOrReadOnlySupplier] # Apply permission class
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_name', 'contact_email', 'description']
    ordering_fields = ['name', 'contact_name', 'created_at']
    ordering = ['name']


class SupplierProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on SupplierProduct model.
    Requires Manager or Owner role for write operations, read-only for others.
    """
    queryset = SupplierProduct.objects.all().order_by('supplier__name', 'product__name')
    serializer_class = SupplierProductSerializer
    permission_classes = [IsManagerOrReadOnlySupplier] # Apply permission class
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'product'] # Filter by supplier and product IDs
    search_fields = ['supplier__name', 'product__name', 'supplier_sku']
    ordering_fields = ['supplier__name', 'product__name', 'supplier_price', 'lead_time_days']


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on PurchaseOrder model.
    Allows staff, managers, and owners to create POs, but management (update, delete)
    is restricted to Managers and Owners. Read-only for others.
    """
    queryset = PurchaseOrder.objects.all().order_by('-po_date') # Default ordering by PO date descending
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsPurchasingManagerOrStaffOrCreatePO] # Apply permission class
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'status', 'po_date', 'expected_delivery_date'] # Filter fields
    search_fields = ['po_number', 'supplier__name', 'notes'] # Search fields
    ordering_fields = ['po_number', 'supplier__name', 'po_date', 'expected_delivery_date', 'status'] # Ordering fields
    ordering = ['-po_date'] # Default ordering


    @action(detail=True, methods=['POST'], url_path='receive-goods', permission_classes=[IsInventoryStaffOrReadOnly]) # Apply permission - adjust if needed
    def receive_goods(self, request, pk=None):
        """
        Action to receive goods for a specific Purchase Order.
        Updates PurchaseOrderItem.quantity_received and Product.stock_quantity.
        """
        purchase_order = self.get_object() # Get the PurchaseOrder instance using pk from URL
        received_items_data = request.data.get('received_items', []) # Get received_items data from request body

        if not isinstance(received_items_data, list):
            return Response({"error": "Received items data must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic(): # Use atomic transaction for data consistency
            for item_data in received_items_data:
                po_item_id = item_data.get('po_item_id')
                quantity_received = item_data.get('quantity_received')

                if not po_item_id or not isinstance(po_item_id, int):
                    return Response({"error": "Invalid po_item_id in received_items data."}, status=status.HTTP_400_BAD_REQUEST)
                if not isinstance(quantity_received, int) or quantity_received < 0:
                    return Response({"error": "Invalid quantity_received. Must be a non-negative integer."}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    po_item = PurchaseOrderItem.objects.get(pk=po_item_id, purchase_order=purchase_order) # Get PO Item, verify it belongs to PO
                except PurchaseOrderItem.DoesNotExist:
                    return Response({"error": f"PurchaseOrderItem with id {po_item_id} not found for this Purchase Order."}, status=status.HTTP_400_BAD_REQUEST)

                if po_item.quantity_received + quantity_received > po_item.quantity_ordered: # Prevent over-receiving
                    return Response({"error": f"Quantity received for item '{po_item.product.name}' exceeds quantity ordered."}, status=status.HTTP_400_BAD_REQUEST)

                product = po_item.product # Get related product

                # Update PurchaseOrderItem.quantity_received
                PurchaseOrderItem.objects.filter(pk=po_item_id).update(quantity_received=F('quantity_received') + quantity_received)
                po_item.refresh_from_db() # Refresh to get updated quantity_received

                # Update Product.stock_quantity - Atomic update using F() expression
                Product.objects.filter(pk=product.pk).update(stock_quantity=F('stock_quantity') + quantity_received)
                product.refresh_from_db() # Refresh product from db

            # Update PurchaseOrder status (basic logic - improve as needed)
            all_items_received = all(item.quantity_received >= item.quantity_ordered for item in purchase_order.po_items.all())
            if all_items_received:
                purchase_order.status = 'received'
            else:
                purchase_order.status = 'partially_received'
            purchase_order.save()

            serializer = self.get_serializer(purchase_order) # Serialize the updated PurchaseOrder
            return Response(serializer.data, status=status.HTTP_200_OK) # Return updated PO data


class PurchaseOrderItemViewSet(viewsets.ModelViewSet): # Optional - if you need direct access to PO Items (usually managed via PO)
    """
    ViewSet for CRUD operations on PurchaseOrderItem model.
    Direct management of PO Items might be restricted in a real application, often managed via PurchaseOrder.
    Permission classes here are just examples and might need adjustment.
    """
    queryset = PurchaseOrderItem.objects.all()
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [IsManagerOrOwnerSupplier] # Example permission - adjust as needed
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['purchase_order', 'product']
    search_fields = ['purchase_order__po_number', 'product__name']
    ordering_fields = ['purchase_order__po_date', 'product__name', 'quantity_ordered', 'unit_price']