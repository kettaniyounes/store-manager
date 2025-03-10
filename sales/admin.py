
# Django Imports
from django.contrib import admin
from .models import PaymentMethod, SaleTransaction, SaleItem
from simple_history.admin import SimpleHistoryAdmin

# Python Imports


@admin.register(PaymentMethod)
class PaymentMethodAdmin(SimpleHistoryAdmin):

    list_display = ('name', 'description', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    fieldsets = (
        ('Payment Method Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


class SaleItemInline(admin.TabularInline): # Inline for Sale Items

    model = SaleItem
    extra = 1
    raw_id_fields = ('product', 'product_variant') # raw_id_fields for product and variant in inline


@admin.register(SaleTransaction)
class SaleTransactionAdmin(SimpleHistoryAdmin):

    list_display = ('transaction_id', 'sale_date', 'customer', 'salesperson', 'payment_method', 'total_amount', 'created_at') # salesperson added
    list_filter = ('sale_date', 'payment_method', 'customer', 'salesperson') # salesperson added
    search_fields = ('transaction_id', 'customer__name', 'salesperson__username') # salesperson__username added, customer__name
    ordering = ('-sale_date',)
    date_hierarchy = 'sale_date' # Date hierarchy for navigation
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'sale_date', 'customer', 'salesperson', 'payment_method', 'status', 'notes') # salesperson added
        }),
        ('Totals', {
            'fields': ('total_amount', 'discount_amount', 'tax_amount'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'total_amount') # total_amount readonly
    inlines = [SaleItemInline] # Add SaleItemInline
    raw_id_fields = ('customer', 'salesperson', 'payment_method') # raw_id_fields for FKs


@admin.register(SaleItem)
class SaleItemAdmin(SimpleHistoryAdmin):
    
    list_display = ('sale_transaction', 'product', 'product_variant', 'quantity', 'unit_price', 'line_total', 'created_at')
    list_filter = ('created_at', 'updated_at', 'sale_transaction', 'product') # Filter by sale transaction, product
    search_fields = ('sale_transaction__transaction_id', 'product__name', 'product_variant__name', 'product_variant__value') # Search related fields
    ordering = ('sale_transaction', 'product')
    fieldsets = (
        ('Sale Item Information', {
            'fields': ('sale_transaction', 'product', 'product_variant', 'quantity', 'unit_price', 'discount_amount', 'tax_amount')
        }),
        ('Totals', {
            'fields': ('line_total',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'line_total') # line_total readonly
    raw_id_fields = ('sale_transaction', 'product', 'product_variant') # raw_id_fields for all FKs