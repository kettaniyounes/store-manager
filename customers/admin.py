
# Django Imports
from django.contrib import admin
from .models import Customer
from simple_history.admin import SimpleHistoryAdmin

# Python Imports


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    
    list_display = ('name', 'phone_number', 'email', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'phone_number', 'email', 'address', 'notes')
    ordering = ('name',)
    fieldsets = (
        ('Customer Information', {
            'fields': ('name', 'phone_number', 'email', 'address', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')