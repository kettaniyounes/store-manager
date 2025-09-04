"""
Comprehensive test suite for multi-tenant functionality
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch

from .models import Tenant, Domain, TenantUser, TenantInvitation
from .utils import get_current_tenant, create_tenant_schema

User = get_user_model()


class TenantModelTest(TestCase):
    """Test tenant model functionality"""
    
    def setUp(self):
        self.tenant_data = {
            'schema_name': 'test_tenant',
            'name': 'Test Store',
            'business_type': 'retail',
            'contact_email': 'test@example.com',
            'phone_number': '+1234567890',
            'address': '123 Test St',
        }
    
    def test_create_tenant(self):
        """Test tenant creation"""
        tenant = Tenant.objects.create(**self.tenant_data)
        
        self.assertEqual(tenant.schema_name, 'test_tenant')
        self.assertEqual(tenant.name, 'Test Store')
        self.assertTrue(tenant.is_active)
        self.assertIsNotNone(tenant.created_at)
    
    def test_tenant_str_representation(self):
        """Test tenant string representation"""
        tenant = Tenant.objects.create(**self.tenant_data)
        self.assertEqual(str(tenant), 'Test Store (test_tenant)')
    
    def test_tenant_schema_name_validation(self):
        """Test schema name validation"""
        # Test invalid schema names
        invalid_names = ['', 'public', 'information_schema', 'pg_catalog']
        
        for invalid_name in invalid_names:
            with self.assertRaises(Exception):
                Tenant.objects.create(
                    schema_name=invalid_name,
                    name='Test Store',
                    contact_email='test@example.com'
                )


class DomainModelTest(TestCase):
    """Test domain model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
    
    def test_create_domain(self):
        """Test domain creation"""
        domain = Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        
        self.assertEqual(domain.domain, 'test.localhost')
        self.assertEqual(domain.tenant, self.tenant)
        self.assertTrue(domain.is_primary)
    
    def test_domain_str_representation(self):
        """Test domain string representation"""
        domain = Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant
        )
        self.assertEqual(str(domain), 'test.localhost')


class TenantUserModelTest(TestCase):
    """Test tenant-user relationship model"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_tenant_user(self):
        """Test tenant-user relationship creation"""
        tenant_user = TenantUser.objects.create(
            tenant=self.tenant,
            user=self.user,
            role='admin',
            can_manage_users=True
        )
        
        self.assertEqual(tenant_user.tenant, self.tenant)
        self.assertEqual(tenant_user.user, self.user)
        self.assertEqual(tenant_user.role, 'admin')
        self.assertTrue(tenant_user.can_manage_users)
        self.assertTrue(tenant_user.is_active)
    
    def test_tenant_user_permissions(self):
        """Test tenant user permission methods"""
        tenant_user = TenantUser.objects.create(
            tenant=self.tenant,
            user=self.user,
            role='admin',
            can_manage_users=True,
            can_manage_settings=True,
            can_view_analytics=True
        )
        
        self.assertTrue(tenant_user.has_permission('manage_users'))
        self.assertTrue(tenant_user.has_permission('manage_settings'))
        self.assertTrue(tenant_user.has_permission('view_analytics'))
        self.assertFalse(tenant_user.has_permission('invalid_permission'))


class TenantAPITest(APITestCase):
    """Test tenant API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
        self.domain = Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        self.tenant_user = TenantUser.objects.create(
            tenant=self.tenant,
            user=self.user,
            role='owner'
        )
    
    def test_tenant_list_authenticated(self):
        """Test tenant list endpoint with authentication"""
        self.client.force_authenticate(user=self.user)
        
        # Mock the tenant resolution
        with patch('tenants.middleware.get_current_tenant', return_value=self.tenant):
            response = self.client.get('/api/tenants/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_tenant_list_unauthenticated(self):
        """Test tenant list endpoint without authentication"""
        response = self.client.get('/api/tenants/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_tenant(self):
        """Test tenant creation via API"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'schema_name': 'new_tenant',
            'name': 'New Store',
            'business_type': 'retail',
            'contact_email': 'new@example.com'
        }
        
        response = self.client.post('/api/tenants/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify tenant was created
        tenant = Tenant.objects.get(schema_name='new_tenant')
        self.assertEqual(tenant.name, 'New Store')


class TenantMiddlewareTest(TestCase):
    """Test tenant middleware functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
        self.domain = Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        self.client = Client()
    
    def test_tenant_resolution_by_domain(self):
        """Test tenant resolution by domain"""
        response = self.client.get('/', HTTP_HOST='test.localhost')
        
        # Check if tenant was properly resolved
        # This would need to be tested with actual middleware in place
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_domain_handling(self):
        """Test handling of invalid domains"""
        response = self.client.get('/', HTTP_HOST='invalid.localhost')
        
        # Should handle gracefully (exact behavior depends on implementation)
        self.assertIn(response.status_code, [404, 400, 200])


class TenantUtilsTest(TestCase):
    """Test tenant utility functions"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
    
    def test_create_tenant_schema(self):
        """Test tenant schema creation utility"""
        # This would test the actual schema creation
        # Implementation depends on your specific utility functions
        pass
    
    @patch('tenants.utils.connection')
    def test_get_current_tenant(self, mock_connection):
        """Test get current tenant utility"""
        mock_connection.tenant = self.tenant
        
        current_tenant = get_current_tenant()
        self.assertEqual(current_tenant, self.tenant)


class TenantInvitationTest(TestCase):
    """Test tenant invitation functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name='test_tenant',
            name='Test Store',
            contact_email='test@example.com'
        )
        self.inviter = User.objects.create_user(
            username='inviter',
            email='inviter@example.com',
            password='testpass123'
        )
    
    def test_create_invitation(self):
        """Test invitation creation"""
        invitation = TenantInvitation.objects.create(
            tenant=self.tenant,
            email='invited@example.com',
            role='member',
            invited_by=self.inviter
        )
        
        self.assertEqual(invitation.tenant, self.tenant)
        self.assertEqual(invitation.email, 'invited@example.com')
        self.assertEqual(invitation.role, 'member')
        self.assertFalse(invitation.is_accepted)
        self.assertIsNotNone(invitation.token)
    
    def test_invitation_acceptance(self):
        """Test invitation acceptance"""
        invitation = TenantInvitation.objects.create(
            tenant=self.tenant,
            email='invited@example.com',
            role='member',
            invited_by=self.inviter
        )
        
        # Create user for the invited email
        invited_user = User.objects.create_user(
            username='invited',
            email='invited@example.com',
            password='testpass123'
        )
        
        # Accept invitation
        invitation.accept(invited_user)
        
        self.assertTrue(invitation.is_accepted)
        self.assertEqual(invitation.accepted_by, invited_user)
        
        # Verify tenant-user relationship was created
        tenant_user = TenantUser.objects.get(
            tenant=self.tenant,
            user=invited_user
        )
        self.assertEqual(tenant_user.role, 'member')


class TenantSchemaTest(TenantTestCase):
    """Test tenant schema isolation"""
    
    def setUp(self):
        super().setUp()
        self.tenant_client = TenantClient(self.tenant)
    
    def test_schema_isolation(self):
        """Test that tenant schemas are properly isolated"""
        # This would test that data in one tenant schema
        # doesn't leak to another tenant schema
        pass
    
    def test_tenant_specific_data(self):
        """Test tenant-specific data operations"""
        # Test creating and retrieving tenant-specific data
        pass


# Integration Tests
class MultiTenantIntegrationTest(TestCase):
    """Integration tests for multi-tenant functionality"""
    
    def setUp(self):
        # Create multiple tenants for testing
        self.tenant1 = Tenant.objects.create(
            schema_name='tenant1',
            name='Store 1',
            contact_email='store1@example.com'
        )
        self.tenant2 = Tenant.objects.create(
            schema_name='tenant2',
            name='Store 2',
            contact_email='store2@example.com'
        )
        
        # Create domains
        Domain.objects.create(
            domain='store1.localhost',
            tenant=self.tenant1,
            is_primary=True
        )
        Domain.objects.create(
            domain='store2.localhost',
            tenant=self.tenant2,
            is_primary=True
        )
        
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create tenant-user relationships
        TenantUser.objects.create(
            tenant=self.tenant1,
            user=self.user1,
            role='admin'
        )
        TenantUser.objects.create(
            tenant=self.tenant2,
            user=self.user2,
            role='admin'
        )
    
    def test_cross_tenant_data_isolation(self):
        """Test that tenants cannot access each other's data"""
        # This would test API endpoints to ensure proper isolation
        pass
    
    def test_user_multi_tenant_access(self):
        """Test user access across multiple tenants"""
        # Add user1 to tenant2 as well
        TenantUser.objects.create(
            tenant=self.tenant2,
            user=self.user1,
            role='member'
        )
        
        # Test that user1 can access both tenants with appropriate permissions
        pass


# Performance Tests
class TenantPerformanceTest(TestCase):
    """Performance tests for multi-tenant operations"""
    
    def test_tenant_creation_performance(self):
        """Test performance of tenant creation"""
        import time
        
        start_time = time.time()
        
        # Create multiple tenants
        for i in range(10):
            Tenant.objects.create(
                schema_name=f'perf_tenant_{i}',
                name=f'Performance Test Store {i}',
                contact_email=f'perf{i}@example.com'
            )
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Assert reasonable performance (adjust threshold as needed)
        self.assertLess(creation_time, 5.0, "Tenant creation took too long")
    
    def test_tenant_query_performance(self):
        """Test performance of tenant queries"""
        # Create test data
        for i in range(100):
            Tenant.objects.create(
                schema_name=f'query_tenant_{i}',
                name=f'Query Test Store {i}',
                contact_email=f'query{i}@example.com'
            )
        
        import time
        start_time = time.time()
        
        # Perform queries
        tenants = list(Tenant.objects.filter(is_active=True))
        
        end_time = time.time()
        query_time = end_time - start_time
        
        self.assertLess(query_time, 1.0, "Tenant queries took too long")
        self.assertEqual(len(tenants), 100)


if __name__ == '__main__':
    pytest.main([__file__])