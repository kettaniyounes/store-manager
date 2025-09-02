
# Django Imports
from django.contrib import admin
from .models import Customer
from simple_history.admin import SimpleHistoryAdmin

# Python Imports


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    
    list_display = ('name', 'phone_number', 'email')
    search_fields = ('name', 'phone_number', 'email', 'address', 'notes')
    ordering = ('name',)
    fieldsets = (
        ('Customer Information', {
            'fields': ('name', 'phone_number', 'email', 'address', 'notes')
        }),
    )
