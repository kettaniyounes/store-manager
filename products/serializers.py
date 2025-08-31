
# Django Import
from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import Category, Brand, ProductImage, ProductVariant, Product

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
            'stock_quantity', 'low_stock_threshold', 'is_active',
            'created_at', 'updated_at', 'images', 'variants', 'product_images','product_variant'  # Include nested fields
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'images', 'variants']  # images and variants are read-only in product serializer for now

    
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

class BarcodeCheckSerializer(serializers.Serializer):
    barcode = serializers.CharField(max_length=255)

    def validate_barcode(self, value):
        if Product.objects.filter(barcode=value).exists():
            raise serializers.ValidationError("This barcode is already in use.")
        return value