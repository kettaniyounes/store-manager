
# Django Imports
from django.contrib import admin
from .models import StoreSetting
from simple_history.admin import SimpleHistoryAdmin

# Python Imports


@admin.register(StoreSetting)
class StoreSettingAdmin(SimpleHistoryAdmin):
    
    list_display = ('key', 'value', 'data_type', 'description', 'created_at', 'updated_at')
    list_filter = ('data_type', 'created_at', 'updated_at', 'key') # Filter by key, data_type
    search_fields = ('key', 'value', 'description')
    ordering = ('key',)
    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value', 'data_type', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'key', 'data_type') # key and data_type readonly after creation