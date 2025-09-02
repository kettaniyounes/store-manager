"""
Monitoring and health check utilities for multi-tenant system
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import time
import psutil
import logging

from .models import TenantOrganization
from .utils import SchemaManager
from .context import TenantContextManager

logger = logging.getLogger(__name__)


class HealthCheckManager:
    """
    Comprehensive health checking for multi-tenant system
    """
    
    def __init__(self):
        self.schema_manager = SchemaManager()
    
    def check_database_health(self):
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'connection_info': {
                    'vendor': connection.vendor,
                    'version': connection.get_server_version(),
                }
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_cache_health(self):
        """Check cache connectivity and performance"""
        try:
            start_time = time.time()
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 30)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            response_time = time.time() - start_time
            
            if retrieved_value == test_value:
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time * 1000, 2)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Cache value mismatch'
                }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_tenant_schemas_health(self):
        """Check health of tenant schemas"""
        try:
            active_tenants = TenantOrganization.objects.filter(is_active=True)
            total_tenants = active_tenants.count()
            healthy_tenants = 0
            unhealthy_tenants = []
            
            for tenant in active_tenants[:10]:  # Check first 10 tenants
                try:
                    with TenantContextManager.set_tenant_context(tenant):
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT 1")
                            cursor.fetchone()
                    healthy_tenants += 1
                except Exception as e:
                    unhealthy_tenants.append({
                        'tenant_id': tenant.id,
                        'tenant_name': tenant.name,
                        'error': str(e)
                    })
            
            return {
                'status': 'healthy' if len(unhealthy_tenants) == 0 else 'degraded',
                'total_tenants': total_tenants,
                'checked_tenants': min(10, total_tenants),
                'healthy_tenants': healthy_tenants,
                'unhealthy_tenants': unhealthy_tenants
            }
        except Exception as e:
            logger.error(f"Tenant schema health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'status': 'healthy',
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_comprehensive_health(self):
        """Get comprehensive health status"""
        health_checks = {
            'database': self.check_database_health(),
            'cache': self.check_cache_health(),
            'tenant_schemas': self.check_tenant_schemas_health(),
            'system_resources': self.check_system_resources(),
            'timestamp': time.time()
        }
        
        # Determine overall status
        statuses = [check['status'] for check in health_checks.values() if isinstance(check, dict) and 'status' in check]
        
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return {
            'overall_status': overall_status,
            'checks': health_checks
        }


class PerformanceMonitor:
    """
    Performance monitoring for multi-tenant operations
    """
    
    def __init__(self):
        self.metrics = {}
    
    def record_tenant_operation(self, operation_type, tenant_id, duration, success=True):
        """Record tenant operation metrics"""
        key = f"tenant_ops_{operation_type}"
        
        if key not in self.metrics:
            self.metrics[key] = {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'min_duration': float('inf'),
                'max_duration': 0
            }
        
        metrics = self.metrics[key]
        metrics['total_operations'] += 1
        
        if success:
            metrics['successful_operations'] += 1
        else:
            metrics['failed_operations'] += 1
        
        metrics['total_duration'] += duration
        metrics['avg_duration'] = metrics['total_duration'] / metrics['total_operations']
        metrics['min_duration'] = min(metrics['min_duration'], duration)
        metrics['max_duration'] = max(metrics['max_duration'], duration)
        
        # Log slow operations
        if duration > 1.0:  # Log operations taking more than 1 second
            logger.warning(
                f"Slow tenant operation: {operation_type} for tenant {tenant_id} "
                f"took {duration:.2f}s"
            )
    
    def get_performance_metrics(self):
        """Get current performance metrics"""
        return self.metrics
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {}


# Global instances
health_checker = HealthCheckManager()
performance_monitor = PerformanceMonitor()


def health_check_view(request):
    """Health check endpoint"""
    health_status = health_checker.get_comprehensive_health()
    
    status_code = 200
    if health_status['overall_status'] == 'unhealthy':
        status_code = 503
    elif health_status['overall_status'] == 'degraded':
        status_code = 200  # Still serving requests
    
    return JsonResponse(health_status, status=status_code)


def performance_metrics_view(request):
    """Performance metrics endpoint"""
    metrics = performance_monitor.get_performance_metrics()
    return JsonResponse({
        'performance_metrics': metrics,
        'timestamp': time.time()
    })