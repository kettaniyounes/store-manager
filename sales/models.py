
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings
from django.utils import timezone
from customers.models import Customer
from products.models import Product, ProductVariant

# Python Imports
from decimal import Decimal
import uuid


class PaymentMethod(models.Model):
    
    name = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name='Payment Method Name'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Description', 
        help_text='Optional description of the payment method'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Is Active', 
        help_text='Indicates if this payment method is currently active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['name']

    def __str__(self):
        return self.name
    

class SaleTransaction(models.Model):
    
    transaction_id = models.CharField(
        max_length=100, 
        unique=True, 
        default=uuid.uuid4,
        verbose_name='Transaction ID', 
        help_text='Unique transaction identifier (e.g., receipt number)'
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sale_transactions', 
        verbose_name='Customer', 
        help_text='Optional customer associated with this sale'
    )
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sale_transactions', 
        verbose_name='Salesperson', 
        help_text='Optional salesperson who processed this sale'
    )
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT, 
        related_name='sale_transactions', 
        verbose_name='Payment Method', 
        help_text='Payment method used for this transaction'
    )
    sale_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Sale Date & Time', 
        help_text='Date and time of the sale transaction'
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Total Amount', 
        help_text='Total amount of the sale transaction (calculated)'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Discount Amount', 
        help_text='Total discount applied to the transaction'
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Tax Amount', 
        help_text='Total tax amount for the transaction'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('completed', 'Completed'),
            ('voided', 'Voided'),
        ],
        default='completed',
        verbose_name='Status',
        help_text='Indicates whether the sale is completed or voided'
    )
    notes = models.TextField(
        blank=True, 
        verbose_name='Notes', 
        help_text='Optional notes or comments for this transaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Sale Transaction'
        verbose_name_plural = 'Sale Transactions'
        ordering = ['-sale_date']

    def __str__(self):
        return self.transaction_id


class SaleItem(models.Model):
    
    sale_transaction = models.ForeignKey(
        SaleTransaction, 
        on_delete=models.CASCADE,
        related_name='sale_items', 
        verbose_name='Sale Transaction'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        related_name='sale_items', 
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='sale_items', 
        verbose_name='Product Variant', 
        help_text='Optional product variant if applicable'
    )
    quantity = models.IntegerField(
        verbose_name='Quantity', 
        help_text='Quantity of the product sold'
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Unit Price', 
        help_text='Price per unit at the time of sale'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Discount Amount', 
        help_text='Discount applied to this sale item'
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Tax Amount', 
        help_text='Tax amount for this sale item'
    )
    line_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Line Total', 
        help_text='Total price for this sale item (calculated)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

    def __str__(self):
        variant_info = f" - Variant: {self.product_variant}" if self.product_variant else ""
        return f"Item for Sale: {self.sale_transaction.transaction_id} - Product: {self.product.name}{variant_info}"
    


