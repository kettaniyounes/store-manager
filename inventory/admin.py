from django.contrib import admin
from .models import StoreInventory, StoreInventoryCount, StoreInventoryCountItem


@admin.register(StoreInventory)
class StoreInventoryAdmin(admin.ModelAdmin):
    list_display = ['store', 'product', 'product_variant', 'quantity_on_hand', 'quantity_available', 'reorder_point']
    list_filter = ['store', 'product__category', 'last_movement_date']
    search_fields = ['product__name', 'product__sku', 'store__name']
    readonly_fields = ['quantity_available', 'last_movement_date', 'created_at', 'updated_at']

@admin.register(StoreInventoryCount)
class StoreInventoryCountAdmin(admin.ModelAdmin):
    list_display = ['count_number', 'store', 'count_date', 'status', 'counted_by']
    list_filter = ['store', 'status', 'count_date']
    search_fields = ['count_number', 'store__name']
    readonly_fields = ['count_number', 'created_at', 'updated_at']


@admin.register(StoreInventoryCountItem)
class StoreInventoryCountItemAdmin(admin.ModelAdmin):
    list_display = ['count', 'product', 'system_quantity', 'counted_quantity', 'variance', 'variance_value']
    list_filter = ['count__store', 'count__count_date']
    search_fields = ['product__name', 'count__count_number']
    readonly_fields = ['variance', 'variance_value', 'created_at', 'updated_at']