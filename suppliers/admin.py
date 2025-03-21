
# Django Imports
from django.contrib import admin
from .models import Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderItem
from simple_history.admin import SimpleHistoryAdmin

# Python Imports



@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin):
    """Admin interface for Supplier model."""

    list_display = ('name', 'contact_name', 'contact_phone', 'contact_email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'contact_name', 'contact_phone', 'contact_email', 'description')
    ordering = ('name',)
    fieldsets = (
        ('Supplier Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Contact Details', {
            'fields': ('contact_name', 'contact_phone', 'contact_email', 'address', 'website')
        }),
        ('Financial Details', {
            'fields': ('payment_terms', 'currency')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SupplierProduct)
class SupplierProductAdmin(SimpleHistoryAdmin):
    """Admin interface for SupplierProduct model."""

    list_display = ('supplier', 'product', 'supplier_sku', 'supplier_price', 'lead_time_days', 'last_price_updated_at')
    list_filter = ('supplier', 'last_price_updated_at')
    search_fields = ('supplier__name', 'product__name', 'supplier_sku')
    ordering = ('supplier__name', 'product__name')
    fieldsets = (
        ('Product Information', {
            'fields': ('supplier', 'product', 'supplier_sku')
        }),
        ('Pricing & Lead Time', {
            'fields': ('supplier_price', 'currency', 'lead_time_days', 'minimum_order_quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_price_updated_at')
    raw_id_fields = ('supplier', 'product') # Use raw_id_fields for ForeignKey


class PurchaseOrderItemInline(admin.TabularInline):
    """Inline for PurchaseOrder Items within PurchaseOrder Admin."""

    model = PurchaseOrderItem
    extra = 1 # Number of empty forms to display
    raw_id_fields = ('product', 'supplier_product') # Use raw_id_fields for ForeignKey


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(SimpleHistoryAdmin):
    """Admin interface for PurchaseOrder model."""

    list_display = ('po_number', 'supplier', 'po_date', 'expected_delivery_date', 'status', 'total_po_value') # Added total_po_value
    list_filter = ('supplier', 'status', 'po_date', 'expected_delivery_date')
    search_fields = ('po_number', 'supplier__name', 'notes')
    ordering = ('-po_date',)
    fieldsets = (
        ('Purchase Order Header', {
            'fields': ('po_number', 'supplier', 'status') # Removed po_date from editable fields
        }),
        ('Addresses & Dates', {
            'fields': ('shipping_address', 'billing_address', 'po_date', 'expected_delivery_date') # Added po_date here for display
        }),
        ('Financial Terms', {
            'fields': ('payment_terms', 'currency')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('po_number', 'po_date', 'created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline] # Add inline for PurchaseOrderItems
    raw_id_fields = ('supplier',) # Use raw_id_fields for ForeignKey

    def total_po_value(self, obj): # Method to display total PO value
        total = sum(item.line_total for item in obj.po_items.all())
        return total
    total_po_value.short_description = 'Total Value' # Column header
    total_po_value.admin_order_field = None # Not sortable

@admin.register(PurchaseOrderItem) # Optionally register PurchaseOrderItem directly if needed
class PurchaseOrderItemAdmin(SimpleHistoryAdmin):
    """Admin interface for PurchaseOrderItem model (optional, mostly managed inline)."""

    list_display = ('purchase_order', 'product', 'quantity_ordered', 'unit_price', 'line_total', 'quantity_received')
    list_filter = ('purchase_order__supplier', 'product__category')
    search_fields = ('purchase_order__po_number', 'product__name')
    ordering = ('purchase_order__po_date', 'product__name')
    fieldsets = (
        ('Item Details', {
            'fields': ('purchase_order', 'product', 'supplier_product', 'quantity_ordered', 'unit_price')
        }),
        ('Pricing & Totals', {
            'fields': ('discount_amount', 'tax_amount', 'line_total')
        }),
        ('Receiving', {
            'fields': ('quantity_received', )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('line_total', 'created_at', 'updated_at')
    raw_id_fields = ('purchase_order', 'product', 'supplier_product') # Use raw_id_fields for ForeignKey