from rest_framework import serializers
from .models import (
    StoreInventory, StoreInventoryCount, StoreInventoryCountItem,
    LocationInventory, PhysicalCount, PhysicalCountItem
)
from settings_app.models import Store
from products.models import Product, ProductVariant


class StoreInventorySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    is_low_stock = serializers.SerializerMethodField()
    needs_reorder = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreInventory
        fields = [
            'id', 'store', 'store_name', 'store_code', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value', 'quantity_on_hand',
            'quantity_reserved', 'quantity_available', 'reorder_point', 'max_stock_level',
            'average_cost', 'is_low_stock', 'needs_reorder', 'last_counted_date',
            'last_movement_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'quantity_available', 'last_movement_date', 'created_at', 'updated_at']
    
    def get_is_low_stock(self, obj):
        return obj.is_low_stock()
    
    def get_needs_reorder(self, obj):
        return obj.needs_reorder()


LocationInventorySerializer = StoreInventorySerializer

class StoreInventoryCountItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    
    class Meta:
        model = StoreInventoryCountItem
        fields = [
            'id', 'count', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'system_quantity', 'counted_quantity', 'variance',
            'unit_cost', 'variance_value', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'variance', 'variance_value', 'created_at', 'updated_at']


class StoreInventoryCountSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.code', read_only=True)
    counted_by_name = serializers.CharField(source='counted_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    count_items = StoreInventoryCountItemSerializer(many=True, read_only=True)
    total_variance_value = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreInventoryCount
        fields = [
            'id', 'count_number', 'store', 'store_name', 'store_code',
            'count_date', 'status', 'counted_by', 'counted_by_name',
            'approved_by', 'approved_by_name', 'notes', 'count_items',
            'total_variance_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'count_number', 'created_at', 'updated_at']
    
    def get_total_variance_value(self, obj):
        return sum(item.variance_value for item in obj.count_items.all())


PhysicalCountSerializer = StoreInventoryCountSerializer


class PhysicalCountItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    
    class Meta:
        model = PhysicalCountItem
        fields = [
            'id', 'count', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'system_quantity', 'counted_quantity', 'variance',
            'unit_cost', 'variance_value', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'variance', 'variance_value', 'created_at', 'updated_at']


class StoreInventoryReportSerializer(serializers.Serializer):
    """Serializer for store inventory reports"""
    
    store_id = serializers.IntegerField()
    store_name = serializers.CharField()
    store_code = serializers.CharField()
    total_products = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    low_stock_items = serializers.IntegerField()
    reorder_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()


class LowStockReportSerializer(serializers.ModelSerializer):
    """Serializer for low stock reports"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    
    class Meta:
        model = LocationInventory
        fields = [
            'id', 'store', 'store_name', 'product', 'product_name', 
            'product_sku', 'category_name', 'quantity_on_hand', 
            'quantity_reserved', 'quantity_available', 'reorder_point'
        ]