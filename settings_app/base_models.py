from django.db import models
from django.core.exceptions import ValidationError
from .context import TenantContextManager
from simple_history.models import HistoricalRecords


class TenantAwareManager(models.Manager):
    """Manager that automatically filters by current tenant context"""
    
    def get_queryset(self):
        """Override to ensure tenant context is applied"""
        queryset = super().get_queryset()
        
        # Get current tenant from context
        tenant = TenantContextManager.get_current_tenant()
        
        # If we have tenant context and the model has a tenant field, filter by it
        if tenant and hasattr(self.model, '_tenant_field'):
            tenant_field = self.model._tenant_field
            filter_kwargs = {tenant_field: tenant}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset
    
    def create(self, **kwargs):
        """Override create to automatically set tenant"""
        tenant = TenantContextManager.get_current_tenant()
        
        if tenant and hasattr(self.model, '_tenant_field'):
            tenant_field = self.model._tenant_field
            if tenant_field not in kwargs:
                kwargs[tenant_field] = tenant
        
        return super().create(**kwargs)


class TenantAwareModel(models.Model):
    """Abstract base model for tenant-aware models"""
    
    # This will be set by subclasses to specify which field links to tenant
    _tenant_field = None
    
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validate tenant context"""
        super().clean()
        
        # Ensure tenant context matches model's tenant
        current_tenant = TenantContextManager.get_current_tenant()
        
        if current_tenant and hasattr(self, '_tenant_field') and self._tenant_field:
            model_tenant = getattr(self, self._tenant_field, None)
            
            if model_tenant and model_tenant != current_tenant:
                raise ValidationError(
                    f"Model tenant ({model_tenant}) does not match current tenant context ({current_tenant})"
                )
    
    def save(self, *args, **kwargs):
        """Override save to ensure tenant context"""
        # Auto-set tenant if not already set
        current_tenant = TenantContextManager.get_current_tenant()
        
        if current_tenant and hasattr(self, '_tenant_field') and self._tenant_field:
            tenant_field_value = getattr(self, self._tenant_field, None)
            if not tenant_field_value:
                setattr(self, self._tenant_field, current_tenant)
        
        # Validate before saving
        self.full_clean()
        
        super().save(*args, **kwargs)


class TenantAwareHistoricalModel(TenantAwareModel):
    """Abstract base model for tenant-aware models with history tracking"""
    
    history = HistoricalRecords(inherit=True)
    
    class Meta:
        abstract = True


class SharedReferenceModel(models.Model):
    """Abstract base model for shared reference data (stored in public schema)"""
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Shared models should not be tenant-specific"""
        super().save(*args, **kwargs)


def tenant_aware_unique_together(*field_names):
    """Helper function to create tenant-aware unique constraints"""
    def decorator(model_class):
        # Add tenant field to unique_together constraints
        if hasattr(model_class._meta, 'unique_together'):
            unique_together = list(model_class._meta.unique_together)
        else:
            unique_together = []
        
        # Add tenant field to each unique constraint
        tenant_field = getattr(model_class, '_tenant_field', None)
        if tenant_field:
            for constraint in unique_together:
                if tenant_field not in constraint:
                    constraint = tuple(list(constraint) + [tenant_field])
            
            # Add new constraint with tenant field
            new_constraint = tuple(list(field_names) + [tenant_field])
            unique_together.append(new_constraint)
            
            model_class._meta.unique_together = unique_together
        
        return model_class
    
    return decorator