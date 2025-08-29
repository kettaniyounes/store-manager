# Django Import
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from .models import (
    PaymentMethod, SaleTransaction, SaleItem, FinancialPeriod,
    ProfitLossReport, SalesAnalytics, TaxReport
)
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
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    variant_value = serializers.CharField(source='product_variant.value', read_only=True)
    quantity = serializers.IntegerField(required=True, min_value=1) # 'quantity' required, min 1
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=Decimal('0.00')) # Make unit_price required
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=Decimal('0.00'))
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gross_profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profit_margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'discount_amount' optional, min 0, default 0
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.00'), default=Decimal('0.00')) # 'tax_amount' optional, min 0, default 0
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # line_total is calculated, read-only

    class Meta:
        model = SaleItem
        fields = [
            'id', 'sale_transaction', 'product', 'product_name', 'product_sku',
            'product_variant', 'variant_name', 'variant_value', 'quantity',
            'unit_price', 'unit_cost', 'total_cost', 'gross_profit', 'profit_margin_percentage',
            'discount_amount', 'tax_amount', 'line_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'line_total', 'sale_transaction', 'total_cost', 'gross_profit', 'profit_margin_percentage'] # sale_transaction is set on backend



class SaleTransactionSerializer(serializers.ModelSerializer):
    
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), allow_null=True, required=False) # Optional customer
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    salesperson = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False) # Optional salesperson
    salesperson_name = serializers.CharField(source='salesperson.username', read_only=True)
    payment_method = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all(), required=True) # Required payment method
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # total_amount is calculated, read-only
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gross_profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profit_margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
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
            'id', 'transaction_id', 'status', 'customer', 'customer_name', 'salesperson', 'salesperson_name', 
            'payment_method', 'payment_method_name', 'sale_date', 'total_amount', 'total_cost', 
            'gross_profit', 'profit_margin_percentage', 'discount_amount', 'tax_amount', 'notes',
            'created_at', 'updated_at', 'sale_items', 'sale_items_input' # Incluade nested sale_items
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount', 'transaction_id', 'status', 'total_cost', 'gross_profit', 'profit_margin_percentage'] # transaction_id might be auto-generated, make it read-only

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
                unit_cost = item_data.get('unit_cost', product.cost_price)
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
                    unit_cost=unit_cost,
                    discount_amount=discount_amount,
                    tax_amount=tax_amount
                ))

            validated_data['total_amount'] = total_transaction_amount
            sale_transaction = SaleTransaction.objects.create(**validated_data)

            for sale_item in sale_items:
                sale_item.sale_transaction = sale_transaction
                sale_item.save()

            # Calculate financial metrics for the transaction
            sale_transaction.calculate_financial_metrics()

        # Now update the product stock directly.
        # If all sale items are for the same product, update it.
        # If multiple products are involved, you might need to iterate per product.
        Product.objects.filter(id=product.id).update(
            stock_quantity=F('stock_quantity') - total_quantity_sold
        )
        product.refresh_from_db()

        return sale_transaction


class FinancialPeriodSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FinancialPeriod
        fields = [
            'id', 'name', 'period_type', 'start_date', 'end_date', 
            'is_closed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProfitLossReportSerializer(serializers.ModelSerializer):
    
    period_name = serializers.CharField(source='period.name', read_only=True)
    period_start_date = serializers.DateField(source='period.start_date', read_only=True)
    period_end_date = serializers.DateField(source='period.end_date', read_only=True)
    
    class Meta:
        model = ProfitLossReport
        fields = [
            'id', 'period', 'period_name', 'period_start_date', 'period_end_date',
            'total_revenue', 'total_cogs', 'gross_profit', 'total_discounts',
            'total_taxes_collected', 'net_profit', 'profit_margin_percentage',
            'transaction_count', 'average_transaction_value', 'generated_at'
        ]
        read_only_fields = ['id', 'generated_at']


class SalesAnalyticsSerializer(serializers.ModelSerializer):
    
    period_name = serializers.CharField(source='period.name', read_only=True)
    period_start_date = serializers.DateField(source='period.start_date', read_only=True)
    period_end_date = serializers.DateField(source='period.end_date', read_only=True)
    top_selling_product_name = serializers.SerializerMethodField()
    best_salesperson_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesAnalytics
        fields = [
            'id', 'period', 'period_name', 'period_start_date', 'period_end_date',
            'total_sales_volume', 'average_items_per_transaction', 'unique_customers',
            'new_customers', 'repeat_customers', 'cash_sales', 'card_sales',
            'other_payment_sales', 'top_selling_product_id', 'top_selling_product_name',
            'top_selling_category_id', 'best_salesperson_id', 'best_salesperson_name',
            'generated_at'
        ]
        read_only_fields = ['id', 'generated_at']
    
    def get_top_selling_product_name(self, obj):
        if obj.top_selling_product_id:
            try:
                product = Product.objects.get(id=obj.top_selling_product_id)
                return product.name
            except Product.DoesNotExist:
                return None
        return None
    
    def get_best_salesperson_name(self, obj):
        if obj.best_salesperson_id:
            try:
                user = User.objects.get(id=obj.best_salesperson_id)
                return user.username
            except User.DoesNotExist:
                return None
        return None


class TaxReportSerializer(serializers.ModelSerializer):
    
    period_name = serializers.CharField(source='period.name', read_only=True)
    period_start_date = serializers.DateField(source='period.start_date', read_only=True)
    period_end_date = serializers.DateField(source='period.end_date', read_only=True)
    
    class Meta:
        model = TaxReport
        fields = [
            'id', 'period', 'period_name', 'period_start_date', 'period_end_date',
            'total_taxable_sales', 'total_tax_collected', 'tax_exempt_sales',
            'average_tax_rate', 'tax_by_rate', 'generated_at'
        ]
        read_only_fields = ['id', 'generated_at']


class DailySalesReportSerializer(serializers.Serializer):
    """Serializer for daily sales summary"""
    
    date = serializers.DateField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_items_sold = serializers.IntegerField()
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)


class MonthlySalesReportSerializer(serializers.Serializer):
    """Serializer for monthly sales summary"""
    
    month = serializers.CharField()
    year = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    growth_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class TopProductsReportSerializer(serializers.Serializer):
    """Serializer for top selling products report"""
    
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    product_sku = serializers.CharField()
    category_name = serializers.CharField()
    total_quantity_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)


class SalespersonPerformanceSerializer(serializers.Serializer):
    """Serializer for salesperson performance report"""
    
    salesperson_id = serializers.IntegerField()
    salesperson_name = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transactions = serializers.IntegerField()
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit_generated = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission_earned = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)