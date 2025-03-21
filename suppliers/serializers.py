
# Django Imports
from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from products.serializers import ProductSerializer  # Import ProductSerializer from products app
from products.models import Product # Import Product model
from .models import Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderItem

# Python Imports

class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for the Supplier model."""

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_name', 'contact_phone', 'contact_email',
            'address', 'website', 'description', 'payment_terms', 'currency',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



class SupplierProductSerializer(serializers.ModelSerializer):
    """Serializer for the SupplierProduct model."""

    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) # Use Product queryset
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name for easier read

    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'product', 'product_name', 'supplier_sku',
            'supplier_price', 'lead_time_days', 'minimum_order_quantity',
            'currency', 'last_price_updated_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_price_updated_at', 'product_name']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for the PurchaseOrderItem model."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) # Use Product queryset
    supplier_product = serializers.PrimaryKeyRelatedField(queryset=SupplierProduct.objects.all(), allow_null=True, required=False)
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name for easier read
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # line_total is calculated, read-only

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'product', 'product_name', 'supplier_product',
            'quantity_ordered', 'unit_price', 'discount_amount', 'tax_amount',
            'line_total', 'quantity_received', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'line_total', 'product_name'] # line_total is read-only, purchase_order is set on backend



class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for the PurchaseOrder model."""

    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=True)
    po_items = PurchaseOrderItemSerializer(many=True, read_only=True, source='po_items.all') # Nested serializer for PO items, read-only for listing/detail
    # Write-only field for creating/updating PO items
    po_items_input = PurchaseOrderItemSerializer(many=True, write_only=True, required=True)

    supplier_name = serializers.CharField(source='supplier.name', read_only=True) # Add supplier name for easier read
    status_display = serializers.CharField(source='get_status_display', read_only=True) # Add status display value
    total_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'po_date', 'expected_delivery_date',
            'shipping_address', 'billing_address', 'payment_terms', 'currency',
            'status', 'status_display', 'notes', 'created_at', 'updated_at',
            'po_items', 'po_items_input','total_value' # Include nested po_items and input field
        ]
        read_only_fields = ['id', 'po_number', 'po_date', 'created_at', 'updated_at', 'status_display', 'supplier_name', 'po_items','total_value'] # po_number and po_date are read-only, po_items is read-only for output

    def validate_po_items_input(self, value):
        """Validates the nested po_items_input data."""
        if not value or not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("Purchase Order must include at least one item.")

        # Validate each item individually
        for item_data in value:
            product_value = item_data.get('product')
            if hasattr(product_value, 'id'):
                item_data['product'] = product_value.id

        for item_data in value:
            serializer = PurchaseOrderItemSerializer(data=item_data)
            serializer.is_valid(raise_exception=True) # Raise exception for any invalid item
        return value

    def create(self, validated_data):
        """Creates a PurchaseOrder instance with nested PurchaseOrderItems."""
        po_items_data = validated_data.pop('po_items_input') # Extract po_items_input

        with transaction.atomic():

            total_value_order = Decimal('0.00')
            po_items = []

            for item_data in po_items_data:
                product_id = item_data['product']
                item_data['product'] = Product.objects.get(id=product_id)
                po_items.append(PurchaseOrderItem(**item_data))
                item_data['line_total'] = (item_data.get('unit_price') * item_data['quantity_ordered']) - item_data.get('discount_amount', 0) + item_data.get('tax_amount', 0)
                total_value_order += item_data['line_total']

            validated_data['total_value'] = total_value_order
            purchase_order = PurchaseOrder.objects.create(**validated_data) # Create PO instance first

            for po_item in po_items:
                po_item.purchase_order = purchase_order
                po_item.save()

        return purchase_order