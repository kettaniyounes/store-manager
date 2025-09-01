# Django Import
from rest_framework import serializers
from .models import StoreSetting, Store, StoreTransfer, StoreTransferItem


# Python Import


class StoreSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.username', read_only=True)
    manager_email = serializers.CharField(source='manager.email', read_only=True)
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'code', 'store_type', 'address', 'city', 
            'state_province', 'postal_code', 'country', 'phone', 'email',
            'manager', 'manager_name', 'manager_email', 'is_active', 
            'is_main_store', 'opening_hours', 'timezone', 'currency', 
            'tax_rate', 'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_address(self, obj):
        """Return formatted full address"""
        return f"{obj.address}, {obj.city}, {obj.state_province} {obj.postal_code}, {obj.country}"
    
    def validate_code(self, value):
        """Ensure store code is uppercase and unique"""
        return value.upper()


class StoreTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    total_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreTransferItem
        fields = [
            'id', 'transfer', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'quantity_requested', 'quantity_shipped', 'quantity_received',
            'unit_cost', 'total_cost', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_cost(self, obj):
        """Calculate total cost based on quantity shipped"""
        return obj.quantity_shipped * obj.unit_cost


class StoreTransferSerializer(serializers.ModelSerializer):
    from_store_name = serializers.CharField(source='from_store.name', read_only=True)
    from_store_code = serializers.CharField(source='from_store.code', read_only=True)
    to_store_name = serializers.CharField(source='to_store.name', read_only=True)
    to_store_code = serializers.CharField(source='to_store.code', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    shipped_by_name = serializers.CharField(source='shipped_by.username', read_only=True)
    received_by_name = serializers.CharField(source='received_by.username', read_only=True)
    transfer_items = StoreTransferItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreTransfer
        fields = [
            'id', 'transfer_number', 'from_store', 'from_store_name', 'from_store_code',
            'to_store', 'to_store_name', 'to_store_code', 'status',
            'requested_by', 'requested_by_name', 'approved_by', 'approved_by_name',
            'shipped_by', 'shipped_by_name', 'received_by', 'received_by_name',
            'request_date', 'shipped_date', 'received_date', 'notes',
            'transfer_items', 'total_items', 'total_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'transfer_number', 'approved_by', 'shipped_by', 'received_by',
            'shipped_date', 'received_date', 'created_at', 'updated_at'
        ]
    
    def get_total_items(self, obj):
        """Get total number of items in transfer"""
        return obj.transfer_items.count()
    
    def get_total_value(self, obj):
        """Calculate total value of transfer"""
        return sum(item.quantity_shipped * item.unit_cost for item in obj.transfer_items.all())
    
    def validate(self, data):
        """Validate transfer data"""
        if data.get('from_store') == data.get('to_store'):
            raise serializers.ValidationError("Source and destination stores cannot be the same.")
        return data


class StoreSettingSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.code', read_only=True)

    key = serializers.ChoiceField(choices=StoreSetting.KEY_CHOICES, required=True)
    value = serializers.CharField(required=True) # 'value' required
    data_type = serializers.ChoiceField(choices=StoreSetting.DATA_TYPE_CHOICES, required=True) # 'data_type' required, use ChoiceField
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = StoreSetting
        fields = [
            'id', 'store', 'store_name', 'store_code', 'key', 'value', 
            'data_type', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'key', 'data_type'] # key and data_type are read-only after creation


class StorePerformanceSerializer(serializers.Serializer):
    """Serializer for store performance metrics"""
    
    store_id = serializers.IntegerField()
    store_name = serializers.CharField()
    store_code = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    inventory_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    low_stock_items = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class StoreComparisonSerializer(serializers.Serializer):
    """Serializer for comparing multiple stores"""
    
    stores = StorePerformanceSerializer(many=True)
    total_company_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_company_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    best_performing_store = serializers.CharField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()