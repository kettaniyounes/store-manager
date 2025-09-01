# Django Import
from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import (
    Category, Brand, ProductImage, ProductVariant, Product,
    StockMovement, StockAdjustment, ProductExpiration
)

# Python Import
from decimal import Decimal
import base64
import uuid


class CategorySerializer(serializers.ModelSerializer):

    name = serializers.CharField(max_length=255, required=True) # Make 'name' explicitly required
    description = serializers.CharField(required=False, allow_blank=True) # 'description' is optional, allow blank

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']



class BrandSerializer(serializers.ModelSerializer):
    
    name = serializers.CharField(max_length=255, required=True) # Make 'name' explicitly required
    description = serializers.CharField(required=False, allow_blank=True) # 'description' is optional, allow blank
    logo = serializers.ImageField(required=False) # 'logo' is optional

    class Meta:
        model = Brand
        fields = ['id', 'name', 'description', 'logo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']



class ProductImageSerializer(serializers.ModelSerializer):

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) # Make 'product' required
    image = serializers.ImageField(required=True) # Make 'image' required
    is_thumbnail = serializers.BooleanField(required=False, default=False) # 'is_thumbnail' optional, default False

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_thumbnail', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        # product field will be handled in ProductSerializer for nested creation/listing


class ProductVariantSerializer(serializers.ModelSerializer):

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) # Make 'product' required
    name = serializers.CharField(max_length=255, required=True) # Make 'name' required
    value = serializers.CharField(max_length=255, required=True) # Make 'value' required
    additional_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False) # 'additional_price' optional
    stock_quantity = serializers.IntegerField(required=False, min_value=Decimal('0.00'), default=0) # 'stock_quantity' optional, default 0, min 0

    class Meta:
        model = ProductVariant
        fields = ['id', 'product', 'name', 'value', 'additional_price', 'stock_quantity', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        # product field will be handled in ProductSerializer for nested creation/listing


class StockMovementSerializer(serializers.ModelSerializer):
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'movement_id', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'movement_type', 'quantity', 'unit_cost', 'total_cost',
            'reference_id', 'notes', 'user', 'user_name',
            'movement_date', 'created_at'
        ]
        read_only_fields = ['id', 'movement_id', 'total_cost', 'created_at']


class StockAdjustmentSerializer(serializers.ModelSerializer):
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StockAdjustment
        fields = [
            'id', 'adjustment_id', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'reason', 'quantity_before', 'quantity_after', 'adjustment_quantity',
            'unit_cost', 'total_value_impact', 'notes', 'user', 'user_name',
            'adjustment_date', 'created_at'
        ]
        read_only_fields = ['id', 'adjustment_id', 'adjustment_quantity', 'total_value_impact', 'created_at']


class ProductExpirationSerializer(serializers.ModelSerializer):
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    days_until_expiration = serializers.SerializerMethodField()
    is_near_expiration = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductExpiration
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value',
            'batch_number', 'quantity', 'manufacture_date', 'expiration_date',
            'unit_cost', 'is_expired', 'days_until_expiration', 'is_near_expiration',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_days_until_expiration(self, obj):
        return obj.days_until_expiration()
    
    def get_is_near_expiration(self, obj):
        return obj.is_near_expiration()


class ProductSerializer(serializers.ModelSerializer):

    name = serializers.CharField(
        max_length=255, 
        required=True
    )  # Make 'name' required
    sku = serializers.CharField(
        max_length=50, 
        required=True
    )  # Make 'sku' required
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=True
    )  # Or SlugRelatedField if using category name/slug
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='brand',
        write_only=True,
        allow_null=True, 
        required=False
    )  # Brand is optional
    cost_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True, 
        min_value=Decimal('0.00')
    )  # 'cost_price' required, min 0
    selling_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True, 
        min_value=Decimal('0.00')
    )  # 'selling_price' required, min 0
    tax_rate = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        required=False, 
        default=Decimal('0.00'), 
        min_value=Decimal('0.00'), 
        max_value=Decimal('100.00')
    )  # 'tax_rate' optional, default 0, range 0-100
    stock_quantity = serializers.IntegerField(
        required=False, 
        default=Decimal('0.00'), 
        min_value=Decimal('0.00')
    )  # 'stock_quantity' optional, default 0, min 0
    low_stock_threshold = serializers.IntegerField(
        required=False, 
        default=Decimal('10.00'), 
        min_value=Decimal('0.00')
    )  # 'low_stock_threshold' optional, default 10, min 0
    reorder_point = serializers.IntegerField(
        required=False,
        default=20,
        min_value=0
    )
    reorder_quantity = serializers.IntegerField(
        required=False,
        default=50,
        min_value=1
    )
    maximum_stock_level = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1
    )
    inventory_valuation_method = serializers.ChoiceField(
        choices=[
            ('fifo', 'First In, First Out (FIFO)'),
            ('lifo', 'Last In, First Out (LIFO)'),
            ('average', 'Weighted Average Cost'),
        ],
        required=False,
        default='fifo'
    )
    is_perishable = serializers.BooleanField(
        required=False,
        default=False
    )
    shelf_life_days = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1
    )
    average_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_inventory_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    is_low_stock = serializers.SerializerMethodField()
    needs_reorder = serializers.SerializerMethodField()
    profit_margin_percentage = serializers.SerializerMethodField()
    profit_per_unit = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(
        required=False, 
        default=True
    )  # 'is_active' optional, default True
    images = ProductImageSerializer(
        many=True, 
        read_only=True, 
        required=False
    )  # Nested serializer for images, read-only in list/detail, create/update via separate image upload
    product_images = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        write_only=True,
        allow_empty=True
    )
    variants = ProductVariantSerializer(
        many=True,
        read_only=True, 
        required=False
    )  # Nested serializer for variants, read-only for now
    product_variant = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        write_only=True,
        allow_empty=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'barcode', 'category', 'brand','category_id', 'brand_id',
            'cost_price', 'selling_price', 'tax_rate', 'unit_of_measurement',
            'stock_quantity', 'low_stock_threshold', 'reorder_point', 'reorder_quantity',
            'maximum_stock_level', 'inventory_valuation_method', 'is_perishable', 'shelf_life_days',
            'average_cost', 'total_inventory_value', 'is_low_stock', 'needs_reorder',
            'profit_margin_percentage', 'profit_per_unit', 'is_active',
            'created_at', 'updated_at', 'images', 'variants', 'product_images','product_variant'  # Include nested fields
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'images', 'variants', 'average_cost', 'total_inventory_value']  # images and variants are read-only in product serializer for now

    def get_is_low_stock(self, obj):
        return obj.is_low_stock()
    
    def get_needs_reorder(self, obj):
        return obj.needs_reorder()
    
    def get_profit_margin_percentage(self, obj):
        return obj.profit_margin_percentage()
    
    def get_profit_per_unit(self, obj):
        return obj.profit_per_unit()
    
    def create(self, validated_data):

        product_images_data = validated_data.pop('product_images', [])
        product_variant_data = validated_data.pop('product_variant', [])
        product = super().create(validated_data)
        for image_data in product_images_data:
            image_base64_string = image_data.get('image', None)  # Use get() to avoid KeyError
            if image_base64_string:
                try:
                    if ';base64,' in image_base64_string:
                        format, imgstr = image_base64_string.split(';base64,')
                    else:
                        imgstr = image_base64_string  # Handle case where there's no format prefix
                    image_data_decoded = base64.b64decode(imgstr)
                    image_file = ContentFile(image_data_decoded, name=f'{product.sku}-{len(product.images.all()) + 1}.png')
                    ProductImage.objects.create(product=product, image=image_file, is_thumbnail=image_data.get('is_thumbnail', False))
                except Exception as e:
                    print(f"Error saving image for product {product.name}: {e}")
        for variant_data in product_variant_data:
            ProductVariant.objects.create(product=product, **variant_data)
        return product


class LowStockReportSerializer(serializers.ModelSerializer):
    """Serializer for low stock report"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    days_of_stock_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name', 'brand_name',
            'stock_quantity', 'low_stock_threshold', 'reorder_point',
            'days_of_stock_remaining', 'selling_price', 'cost_price'
        ]
    
    def get_days_of_stock_remaining(self, obj):
        # This would need sales velocity data to calculate accurately
        # For now, return a placeholder calculation
        if obj.stock_quantity > 0:
            return obj.stock_quantity / max(1, obj.low_stock_threshold) * 7  # Rough estimate
        return 0


class ReorderReportSerializer(serializers.ModelSerializer):
    """Serializer for reorder report"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    suggested_order_quantity = serializers.SerializerMethodField()
    estimated_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name', 'brand_name',
            'stock_quantity', 'reorder_point', 'reorder_quantity',
            'suggested_order_quantity', 'estimated_cost', 'cost_price'
        ]
    
    def get_suggested_order_quantity(self, obj):
        return obj.reorder_quantity
    
    def get_estimated_cost(self, obj):
        return obj.reorder_quantity * obj.cost_price


class InventoryValuationSerializer(serializers.ModelSerializer):
    """Serializer for inventory valuation report"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    total_cost_value = serializers.SerializerMethodField()
    total_selling_value = serializers.SerializerMethodField()
    potential_profit = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name', 'brand_name',
            'stock_quantity', 'cost_price', 'selling_price', 'average_cost',
            'total_cost_value', 'total_selling_value', 'potential_profit',
            'inventory_valuation_method'
        ]
    
    def get_total_cost_value(self, obj):
        return obj.stock_quantity * obj.average_cost
    
    def get_total_selling_value(self, obj):
        return obj.stock_quantity * obj.selling_price
    
    def get_potential_profit(self, obj):
        return (obj.stock_quantity * obj.selling_price) - (obj.stock_quantity * obj.average_cost)


class BarcodeCheckSerializer(serializers.Serializer):
    barcode = serializers.CharField(max_length=255)

    def validate_barcode(self, value):
        if Product.objects.filter(barcode=value).exists():
            raise serializers.ValidationError("This barcode is already in use.")
        return value