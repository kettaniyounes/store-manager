from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tenant, TenantUser, TenantInvitation
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import connection


class TenantSerializer(serializers.ModelSerializer):
    """
    Serializer for Tenant model with comprehensive field coverage.
    """
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'schema_name', 'business_type', 'contact_email', 
            'contact_phone', 'address_line1', 'address_line2', 'city', 
            'state', 'postal_code', 'country', 'subscription_plan', 
            'is_active', 'timezone', 'currency', 'created_on'
        ]
        read_only_fields = ['id', 'created_on']


class TenantUserSerializer(serializers.ModelSerializer):
    """
    Serializer for TenantUser relationships.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = TenantUser
        fields = [
            'id', 'user', 'user_email', 'user_username', 'tenant', 
            'tenant_name', 'role', 'is_active', 'can_manage_users', 
            'can_manage_settings', 'can_view_analytics', 
            'can_manage_inventory', 'can_process_sales', 'joined_on'
        ]
        read_only_fields = ['id', 'joined_on']


class TenantInvitationSerializer(serializers.ModelSerializer):
    """
    Serializer for tenant invitations.
    """
    invited_by_username = serializers.CharField(source='invited_by.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = TenantInvitation
        fields = [
            'id', 'tenant', 'tenant_name', 'invited_by', 
            'invited_by_username', 'email', 'role', 'token', 
            'is_accepted', 'is_expired', 'created_on', 'expires_on'
        ]
        read_only_fields = ['id', 'token', 'created_on', 'accepted_on']


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes tenant information in the token.
    """
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Get current tenant from connection
        tenant = getattr(connection, 'tenant', None)
        
        if tenant:
            # Add tenant information to the token
            self.token['tenant_id'] = str(tenant.id)
            self.token['tenant_name'] = tenant.name
            self.token['tenant_slug'] = tenant.slug
            
            # Get user's role in this tenant
            try:
                tenant_user = TenantUser.objects.get(
                    user=self.user, 
                    tenant=tenant,
                    is_active=True
                )
                self.token['tenant_role'] = tenant_user.role
                self.token['tenant_permissions'] = {
                    'can_manage_users': tenant_user.can_manage_users,
                    'can_manage_settings': tenant_user.can_manage_settings,
                    'can_view_analytics': tenant_user.can_view_analytics,
                    'can_manage_inventory': tenant_user.can_manage_inventory,
                    'can_process_sales': tenant_user.can_process_sales,
                }
            except TenantUser.DoesNotExist:
                # User doesn't belong to this tenant
                raise serializers.ValidationError(
                    "User does not have access to this tenant."
                )
        
        return data