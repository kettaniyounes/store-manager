
# Django Import
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from .models import PaymentMethod, SaleTransaction, SaleItem
from products.models import Product, ProductVariant
from customers.models import Customer

# Python Import
from decimal import Decimal

class PaymentMethodSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SaleItemSerializer(serializers.ModelSerializer):

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True) # Use PrimaryKeyRelatedField for product
    product_variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all(), allow_null=True, required=False) # Optional variant
    quantity = serializers.IntegerField(required=True, min_value=1) # 'quantity' required, min 1
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=Decimal('0.00')) # Make unit_price required
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'discount_amount' optional, min 0, default 0
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'tax_amount' optional, min 0, default 0
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # line_total is calculated, read-only

    class Meta:
        model = SaleItem
        fields = [
            'id', 'sale_transaction', 'product', 'product_variant', 'quantity',
            'unit_price', 'discount_amount', 'tax_amount', 'line_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'line_total', 'sale_transaction'] # sale_transaction is set on backend



class SaleTransactionSerializer(serializers.ModelSerializer):
    
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), allow_null=True, required=False) # Optional customer
    salesperson = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False) # Optional salesperson
    payment_method = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all(), required=True) # Required payment method
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # total_amount is calculated, read-only
    sale_date = serializers.DateTimeField(required=False) # 'sale_date' optional (defaults to now)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'discount_amount' optional, min 0, default 0
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'tax_amount' optional, min 0, default 0
    notes = serializers.CharField(required=False, allow_blank=True) # 'notes' optional, allow blank
    #sale_items = SaleItemSerializer(many=True, write_only=True) # Nested SaleItemSerializer, write_only for creation/update
    # Read-only field for output (nested sale items, obtained via reverse relation)
    sale_items = SaleItemSerializer(many=True, read_only=True, required=False)
    
    # Write-only field for input data
    sale_items_input = serializers.ListField(
        child=SaleItemSerializer(), write_only=True, required=True, min_length=1
    )


    class Meta:
        model = SaleTransaction
        fields = [
            'id', 'transaction_id', 'status', 'customer', 'salesperson', 'payment_method',
            'sale_date', 'total_amount', 'discount_amount', 'tax_amount', 'notes',
            'created_at', 'updated_at', 'sale_items', 'sale_items_input' # Incluade nested sale_items
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount', 'transaction_id', 'status'] # transaction_id might be auto-generated, make it read-only

    def validate_sale_items_input(self, value):

        if not value or not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("Sale must include at least one sale item.")
        for item_data in value:
            # If 'product' is already a Product instance, convert it back to its primary key.
            product_value = item_data.get('product')
            if hasattr(product_value, 'id'):
                item_data['product'] = product_value.id
            product_variant_value = item_data.get('product_variant')
            if hasattr(product_variant_value, 'id'):
                item_data['product_variant'] = product_variant_value.id

            # Validate each sale item individually.
            serializer = SaleItemSerializer(data=item_data)
            serializer.is_valid(raise_exception=True)
        return value

    def create(self, validated_data):
        
        sale_items_data = validated_data.pop('sale_items_input')
        with transaction.atomic():
            total_transaction_amount = Decimal('0.00')
            sale_items = []
            total_quantity_sold = 0

            for item_data in sale_items_data:
                product_id = item_data['product']
                product = Product.objects.get(id=product_id)
                product_variant_id = item_data.get('product_variant', None)
                product_variant = ProductVariant.objects.get(id=product_variant_id) if product_variant_id else None
                quantity = item_data['quantity']
                unit_price = item_data['unit_price']
                discount_amount = item_data.get('discount_amount', Decimal('0.00'))
                tax_amount = item_data.get('tax_amount', Decimal('0.00'))

                line_total = (unit_price - discount_amount) * quantity + tax_amount
                total_transaction_amount += line_total
                total_quantity_sold += quantity

                sale_items.append(SaleItem(
                    sale_transaction=None,  # Temporarily set to None
                    line_total=line_total,
                    product=product,
                    product_variant=product_variant,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_amount=discount_amount,
                    tax_amount=tax_amount
                ))

            validated_data['total_amount'] = total_transaction_amount
            sale_transaction = SaleTransaction.objects.create(**validated_data)

            for sale_item in sale_items:
                sale_item.sale_transaction = sale_transaction
                sale_item.save()

        # Now update the product stock directly.
        # If all sale items are for the same product, update it.
        # If multiple products are involved, you might need to iterate per product.
        Product.objects.filter(id=product.id).update(
            stock_quantity=F('stock_quantity') - total_quantity_sold
        )
        product.refresh_from_db()

        return sale_transaction