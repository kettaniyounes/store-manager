from rest_framework import serializers
from django.db import models
from .context import TenantContextManager
from .base_models import TenantAwareHistoricalModel, SharedReferenceModel


class TenantAwareModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for tenant-aware models that automatically handles tenant context
    """
    
    def create(self, validated_data):
        """Automatically set tenant context for new instances"""
        instance = super().create(validated_data)
        
        # Ensure the instance is saved in the correct tenant schema
        current_tenant = TenantContextManager.get_current_tenant()
        if current_tenant and hasattr(instance._meta.model, '_tenant_field'):
            tenant_field = instance._meta.model._tenant_field
            if not getattr(instance, tenant_field, None):
                setattr(instance, tenant_field, current_tenant)
                instance.save()
        
        return instance
    
    def validate(self, attrs):
        """Add tenant-aware validation"""
        attrs = super().validate(attrs)
        
        # Validate foreign key references are within tenant scope
        current_tenant = TenantContextManager.get_current_tenant()
        if current_tenant:
            for field_name, value in attrs.items():
                field = self.fields.get(field_name)
                if isinstance(field, serializers.PrimaryKeyRelatedField) and value:
                    # Check if the related object belongs to the current tenant
                    if hasattr(value, '_meta') and hasattr(value._meta.model, '_tenant_field'):
                        tenant_field = value._meta.model._tenant_field
                        if getattr(value, tenant_field, None) != current_tenant:
                            raise serializers.ValidationError(
                                f"{field_name}: Referenced object does not belong to current tenant"
                            )
        
        return attrs


class SharedReferenceModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for shared reference models (global across tenants)
    """
    
    class Meta:
        abstract = True
    
    def validate(self, attrs):
        """Validate shared reference model data"""
        attrs = super().validate(attrs)
        
        # Add any global validation logic here
        return attrs


class TenantFilteredPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Custom PrimaryKeyRelatedField that automatically filters by tenant context
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # If the model is tenant-aware, filter by current tenant
        if hasattr(queryset.model, 'objects') and hasattr(queryset.model.objects, 'get_queryset'):
            # Use the tenant-aware manager if available
            if hasattr(queryset.model, '_tenant_field'):
                current_tenant = TenantContextManager.get_current_tenant()
                if current_tenant:
                    tenant_field = queryset.model._tenant_field
                    queryset = queryset.filter(**{tenant_field: current_tenant})
        
        return queryset


class TenantAwareChoiceField(serializers.ChoiceField):
    """
    Choice field that can be filtered by tenant context if needed
    """
    
    def __init__(self, **kwargs):
        self.tenant_filtered = kwargs.pop('tenant_filtered', False)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        # Add tenant-specific choice validation if needed
        return super().to_internal_value(data)