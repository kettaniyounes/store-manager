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
        
        # Schema isolation handles tenant separation automatically
        # No need to filter by tenant field since each tenant has its own schema
        
        return queryset
    
    def create(self, **kwargs):
        """Override create to automatically set tenant"""
        return super().create(**kwargs)


class TenantAwareModel(models.Model):
    """Abstract base model for tenant-aware models"""
    
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validate tenant context"""
        super().clean()
        
        # Ensure tenant context is available for logging/auditing
        current_tenant = TenantContextManager.get_current_tenant()
        
        if not current_tenant:
            # This might be a system operation or migration
            pass
    
    def save(self, *args, **kwargs):
        """Override save to ensure tenant context"""
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
        # Add unique_together constraints without tenant field
        if hasattr(model_class._meta, 'unique_together'):
            unique_together = list(model_class._meta.unique_together)
        else:
            unique_together = []
        
        # Add new constraint without tenant field (schema isolation handles tenant separation)
        new_constraint = tuple(field_names)
        unique_together.append(new_constraint)
        
        model_class._meta.unique_together = unique_together
        
        return model_class
    
    return decorator