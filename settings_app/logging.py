"""
Custom logging utilities for multi-tenant application
"""
import logging
from .context import TenantContextManager


class TenantLogFilter(logging.Filter):
    """
    Logging filter that adds tenant information to log records
    """
    
    def filter(self, record):
        tenant = TenantContextManager.get_current_tenant()
        if tenant:
            record.tenant_id = tenant.id
            record.tenant_name = tenant.name
            record.tenant_schema = tenant.schema_name
        else:
            record.tenant_id = 'public'
            record.tenant_name = 'Public'
            record.tenant_schema = 'public'
        
        return True


class TenantLogger:
    """
    Utility class for tenant-aware logging
    """
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def log_tenant_operation(self, level, message, tenant=None, **kwargs):
        """Log tenant-specific operations"""
        if not tenant:
            tenant = TenantContextManager.get_current_tenant()
        
        extra = {
            'tenant_id': tenant.id if tenant else 'public',
            'tenant_name': tenant.name if tenant else 'Public',
            **kwargs
        }
        
        self.logger.log(level, message, extra=extra)
    
    def info(self, message, **kwargs):
        self.log_tenant_operation(logging.INFO, message, **kwargs)
    
    def warning(self, message, **kwargs):
        self.log_tenant_operation(logging.WARNING, message, **kwargs)
    
    def error(self, message, **kwargs):
        self.log_tenant_operation(logging.ERROR, message, **kwargs)
    
    def debug(self, message, **kwargs):
        self.log_tenant_operation(logging.DEBUG, message, **kwargs)


# Global tenant logger instance
tenant_logger = TenantLogger('tenant_operations')