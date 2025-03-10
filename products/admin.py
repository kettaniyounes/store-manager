
# Django Imports
from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, ProductVariant
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html

# Python Imports


@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin): # Inherit from SimpleHistoryAdmin for history in admin

    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')
    ordering = ('name',)
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',), # Collapse this fieldset by default
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Brand)
class BrandAdmin(SimpleHistoryAdmin):

    list_display = ('name', 'description', 'logo_preview', 'created_at', 'updated_at') # Added logo_preview
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')
    ordering = ('name',)
    fieldsets = (
        ('Brand Information', {
            'fields': ('name', 'description', 'logo')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def logo_preview(self, obj): # Custom method to display logo thumbnail in admin list
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.logo.url)
        return '-'
    logo_preview.short_description = 'Logo Preview' # Column header for logo preview
    logo_preview.allow_tags = True # Allow HTML in logo preview


class ProductImageInline(admin.TabularInline): # Inline for Product Images

    model = ProductImage
    extra = 1 # Number of empty forms to display
    readonly_fields = ('image_preview',) # Make image_preview readonly

    def image_preview(self, obj): # Custom method for image preview in inline
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Image Preview'
    image_preview.allow_tags = True

class ProductVariantInline(admin.TabularInline): # Inline for Product Variants

    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):

    list_display = ('name', 'sku', 'category', 'brand', 'selling_price', 'stock_quantity', 'is_active', 'created_at', 'updated_at')
    list_filter = ('category', 'brand', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'sku', 'description', 'barcode')
    ordering = ('name',)
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'sku', 'barcode', 'is_active')
        }),
        ('Pricing & Stock', {
            'fields': ('category', 'brand', 'cost_price', 'selling_price', 'tax_rate', 'unit_of_measurement', 'stock_quantity', 'low_stock_threshold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductImageInline, ProductVariantInline] # Add inlines for images and variants
    raw_id_fields = ('category', 'brand') # Use raw_id_fields for category and brand FKs if tables become large


@admin.register(ProductImage)
class ProductImageAdmin(SimpleHistoryAdmin):

    list_display = ('product', 'image_preview', 'is_thumbnail', 'created_at', 'updated_at') # Added image_preview
    list_filter = ('is_thumbnail', 'created_at', 'updated_at', 'product') # Filter by product
    search_fields = ('product__name',) # Search by product name (related field)
    ordering = ('product', '-created_at') # Order by product and creation date
    fieldsets = (
        ('Image Information', {
            'fields': ('product', 'image', 'is_thumbnail')
        }),
        ('Image Preview', { # Added fieldset for preview in form
            'fields': ('image_preview',),
            'classes': ('collapse', 'wide', 'extrapretty'), # Example classes for styling
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'image_preview') # image_preview readonly

    def image_preview(self, obj): # Reused image_preview method from ProductImageInline
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.image.url) # Larger preview in form
        return '-'
    image_preview.short_description = 'Image Preview'
    image_preview.allow_tags = True
    image_preview.classes = ('readonly',) # Example class for styling preview field
    raw_id_fields = ('product',) # raw_id_field for product FK


@admin.register(ProductVariant)
class ProductVariantAdmin(SimpleHistoryAdmin):
    
    list_display = ('product', 'name', 'value', 'additional_price', 'stock_quantity', 'created_at', 'updated_at')
    list_filter = ('name', 'created_at', 'updated_at', 'product') # Filter by product, variant name
    search_fields = ('product__name', 'name', 'value') # Search by product name, variant name, value
    ordering = ('product', 'name', 'value')
    fieldsets = (
        ('Variant Information', {
            'fields': ('product', 'name', 'value', 'additional_price', 'stock_quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('product',) # raw_id_field for product FK