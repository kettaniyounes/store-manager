"""
Multi-tenant testing utilities and fixtures
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.contrib.auth.models import User
from django.conf import settings
from unittest.mock import patch
from contextlib import contextmanager

from .models import TenantOrganization
from .utils import SchemaManager
from .context import TenantContextManager
from store_management_backend.middleware import TenantResolutionMiddleware


class TenantTestMixin:
    """
    Mixin for test classes that need multi-tenant functionality
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema_manager = SchemaManager()
        cls.test_tenants = {}
    
    @classmethod
    def tearDownClass(cls):
        # Clean up test tenant schemas
        for tenant_id, tenant in cls.test_tenants.items():
            try:
                cls.schema_manager.drop_tenant_schema(tenant.schema_name)
            except Exception:
                pass  # Schema might not exist
        super().tearDownClass()
    
    def create_test_tenant(self, name, schema_name=None, domain=None):
        """Create a test tenant with schema"""
        if schema_name is None:
            schema_name = f"test_{name.lower().replace(' ', '_')}"
        
        if domain is None:
            domain = f"{name.lower().replace(' ', '-')}.testdomain.com"
        
        tenant = TenantOrganization.objects.create(
            name=name,
            schema_name=schema_name,
            domain=domain,
            subdomain=name.lower().replace(' ', '-'),
            is_active=True
        )
        
        # Create schema and run migrations
        self.schema_manager.create_tenant_schema(schema_name)
        self.schema_manager.migrate_tenant_schema(schema_name)
        
        self.test_tenants[tenant.id] = tenant
        return tenant
    
    @contextmanager
    def tenant_context(self, tenant):
        """Context manager for executing code in tenant context"""
        with TenantContextManager.set_tenant_context(tenant):
            yield
    
    def switch_to_tenant(self, tenant):
        """Switch database connection to tenant schema"""
        self.schema_manager.set_tenant_schema(tenant.schema_name)
        TenantContextManager.set_tenant_context(tenant)
    
    def switch_to_public(self):
        """Switch back to public schema"""
        self.schema_manager.set_tenant_schema('public')
        TenantContextManager.set_tenant_context(None)


class TenantTestCase(TenantTestMixin, TestCase):
    """
    Base test case for multi-tenant tests using Django TestCase
    """
    pass


class TenantTransactionTestCase(TenantTestMixin, TransactionTestCase):
    """
    Base test case for multi-tenant tests that need transaction control
    """
    pass


@pytest.fixture
def tenant_factory():
    """Factory for creating test tenants"""
    created_tenants = []
    schema_manager = SchemaManager()
    
    def _create_tenant(name, schema_name=None, domain=None):
        if schema_name is None:
            schema_name = f"test_{name.lower().replace(' ', '_')}"
        
        if domain is None:
            domain = f"{name.lower().replace(' ', '-')}.testdomain.com"
        
        tenant = TenantOrganization.objects.create(
            name=name,
            schema_name=schema_name,
            domain=domain,
            subdomain=name.lower().replace(' ', '-'),
            is_active=True
        )
        
        # Create schema and run migrations
        schema_manager.create_tenant_schema(schema_name)
        schema_manager.migrate_tenant_schema(schema_name)
        
        created_tenants.append(tenant)
        return tenant
    
    yield _create_tenant
    
    # Cleanup
    for tenant in created_tenants:
        try:
            schema_manager.drop_tenant_schema(tenant.schema_name)
            tenant.delete()
        except Exception:
            pass


@pytest.fixture
def sample_tenants(tenant_factory):
    """Create sample tenants for testing"""
    tenant_a = tenant_factory("Tenant A", "test_tenant_a")
    tenant_b = tenant_factory("Tenant B", "test_tenant_b")
    return {'tenant_a': tenant_a, 'tenant_b': tenant_b}


@pytest.fixture
def tenant_context_manager():
    """Context manager for tenant switching in tests"""
    @contextmanager
    def _tenant_context(tenant):
        with TenantContextManager.set_tenant_context(tenant):
            yield
    
    return _tenant_context


class TenantIsolationTestMixin:
    """
    Mixin for testing tenant data isolation
    """
    
    def assert_tenant_isolation(self, model_class, tenant_a, tenant_b, create_data_func):
        """
        Test that data created in one tenant is not visible in another
        
        Args:
            model_class: The model class to test
            tenant_a: First tenant
            tenant_b: Second tenant  
            create_data_func: Function that creates test data, receives tenant as parameter
        """
        # Create data in tenant A
        with TenantContextManager.set_tenant_context(tenant_a):
            data_a = create_data_func(tenant_a)
            count_a = model_class.objects.count()
            assert count_a > 0, "Data should be created in tenant A"
        
        # Switch to tenant B and verify isolation
        with TenantContextManager.set_tenant_context(tenant_b):
            count_b = model_class.objects.count()
            assert count_b == 0, "Tenant B should not see tenant A's data"
            
            # Create different data in tenant B
            data_b = create_data_func(tenant_b)
            count_b_after = model_class.objects.count()
            assert count_b_after > 0, "Data should be created in tenant B"
        
        # Switch back to tenant A and verify data is still there
        with TenantContextManager.set_tenant_context(tenant_a):
            count_a_final = model_class.objects.count()
            assert count_a_final == count_a, "Tenant A data should be unchanged"
    
    def assert_cross_tenant_reference_blocked(self, model_class, foreign_key_field, tenant_a, tenant_b, create_data_func):
        """
        Test that cross-tenant foreign key references are blocked
        """
        # Create reference data in tenant A
        with TenantContextManager.set_tenant_context(tenant_a):
            ref_data_a = create_data_func(tenant_a)
        
        # Try to create data in tenant B that references tenant A data
        with TenantContextManager.set_tenant_context(tenant_b):
            with pytest.raises(Exception):  # Should raise validation error
                model_class.objects.create(**{foreign_key_field: ref_data_a})


class MiddlewareTestMixin:
    """
    Mixin for testing tenant resolution middleware
    """
    
    def create_request_with_tenant(self, tenant, method='GET', path='/', **kwargs):
        """Create a request with tenant context"""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = getattr(factory, method.lower())(path, **kwargs)
        
        # Add tenant resolution headers/domain
        request.META['HTTP_HOST'] = tenant.domain
        request.META['HTTP_X_TENANT_ID'] = str(tenant.id)
        
        return request
    
    def test_tenant_resolution_methods(self, tenant, middleware_instance):
        """Test different tenant resolution methods"""
        # Test subdomain resolution
        request = self.create_request_with_tenant(tenant)
        request.META['HTTP_HOST'] = f"{tenant.subdomain}.testdomain.com"
        
        resolved_tenant = middleware_instance._resolve_tenant_from_subdomain(request)
        assert resolved_tenant == tenant
        
        # Test header resolution
        request = self.create_request_with_tenant(tenant)
        resolved_tenant = middleware_instance._resolve_tenant_from_header(request)
        assert resolved_tenant == tenant
        
        # Test domain resolution
        request = self.create_request_with_tenant(tenant)
        resolved_tenant = middleware_instance._resolve_tenant_from_domain(request)
        assert resolved_tenant == tenant


class PerformanceTestMixin:
    """
    Mixin for testing multi-tenant performance
    """
    
    def measure_schema_switch_time(self, tenant_a, tenant_b, iterations=100):
        """Measure time taken for schema switching"""
        import time
        
        schema_manager = SchemaManager()
        
        start_time = time.time()
        for i in range(iterations):
            if i % 2 == 0:
                schema_manager.set_tenant_schema(tenant_a.schema_name)
            else:
                schema_manager.set_tenant_schema(tenant_b.schema_name)
        
        end_time = time.time()
        avg_time = (end_time - start_time) / iterations
        
        # Assert reasonable performance (adjust threshold as needed)
        assert avg_time < 0.01, f"Schema switching too slow: {avg_time}s per switch"
        
        return avg_time
    
    def measure_query_performance_with_tenants(self, model_class, tenant, num_records=1000):
        """Measure query performance within tenant context"""
        import time
        
        with TenantContextManager.set_tenant_context(tenant):
            # Create test data
            for i in range(num_records):
                model_class.objects.create(name=f"Test Record {i}")
            
            # Measure query time
            start_time = time.time()
            list(model_class.objects.all())
            end_time = time.time()
            
            query_time = end_time - start_time
            
            # Assert reasonable performance
            assert query_time < 1.0, f"Query too slow: {query_time}s for {num_records} records"
            
            return query_time


def create_test_user_in_tenant(tenant, username="testuser", email="test@example.com", **kwargs):
    """Create a test user within tenant context"""
    with TenantContextManager.set_tenant_context(tenant):
        user = User.objects.create_user(
            username=username,
            email=email,
            **kwargs
        )
        return user


def assert_tenant_data_isolation(tenant_a, tenant_b, model_class, create_func):
    """
    Utility function to test data isolation between tenants
    """
    # Create data in tenant A
    with TenantContextManager.set_tenant_context(tenant_a):
        obj_a = create_func()
        count_a = model_class.objects.count()
        assert count_a == 1
    
    # Verify tenant B doesn't see the data
    with TenantContextManager.set_tenant_context(tenant_b):
        count_b = model_class.objects.count()
        assert count_b == 0
        
        # Create data in tenant B
        obj_b = create_func()
        count_b_after = model_class.objects.count()
        assert count_b_after == 1
    
    # Verify tenant A still has its data
    with TenantContextManager.set_tenant_context(tenant_a):
        count_a_final = model_class.objects.count()
        assert count_a_final == 1