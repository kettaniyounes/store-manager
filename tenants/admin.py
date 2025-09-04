from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Tenant, Domain, TenantUser, TenantInvitation


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    """
    Admin interface for managing tenants.
    """
    list_display = [
        'name', 'slug', 'business_type', 'subscription_plan', 
        'is_active', 'created_on', 'trial_end_date'
    ]
    list_filter = ['business_type', 'subscription_plan', 'is_active', 'created_on']
    search_fields = ['name', 'slug', 'contact_email', 'city']
    readonly_fields = ['id', 'created_on', 'updated_on', 'schema_name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'business_type', 'schema_name')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city', 
                'state', 'postal_code', 'country'
            )
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'trial_end_date', 'is_active')
        }),
        ('Settings', {
            'fields': ('timezone', 'currency')
        }),
        ('Timestamps', {
            'fields': ('created_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tenant domains.
    """
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tenant-user relationships.
    """
    list_display = [
        'user', 'tenant', 'role', 'is_active', 
        'can_manage_users', 'joined_on'
    ]
    list_filter = ['role', 'is_active', 'can_manage_users', 'can_manage_settings']
    search_fields = ['user__username', 'user__email', 'tenant__name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'tenant', 'role', 'is_active')
        }),
        ('Permissions', {
            'fields': (
                'can_manage_users', 'can_manage_settings', 
                'can_view_analytics', 'can_manage_inventory', 
                'can_process_sales'
            )
        }),
        ('Timestamps', {
            'fields': ('joined_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tenant invitations.
    """
    list_display = [
        'email', 'tenant', 'role', 'invited_by', 
        'is_accepted', 'is_expired', 'created_on'
    ]
    list_filter = ['role', 'is_accepted', 'is_expired', 'created_on']
    search_fields = ['email', 'tenant__name', 'invited_by__username']
    readonly_fields = ['token', 'created_on', 'accepted_on']