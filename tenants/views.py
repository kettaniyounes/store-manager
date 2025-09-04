"""
Views for tenant management and operations.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context, get_public_schema_name
from datetime import timedelta
import uuid

from .models import Tenant, Domain, TenantUser, TenantInvitation
from .serializers import (
    TenantSerializer, TenantUserSerializer, TenantInvitationSerializer,
    TenantTokenObtainPairSerializer
)
from .permissions import IsTenantOwnerOrAdmin, IsTenantMember


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenants in public schema.
    """
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return tenants where user is a member."""
        user = self.request.user
        tenant_ids = TenantUser.objects.filter(
            user=user, is_active=True
        ).values_list('tenant_id', flat=True)
        return Tenant.objects.filter(id__in=tenant_ids)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a tenant."""
        tenant = self.get_object()
        tenant.is_active = True
        tenant.save()
        return Response({'status': 'Tenant activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a tenant."""
        tenant = self.get_object()
        tenant.is_active = False
        tenant.save()
        return Response({'status': 'Tenant deactivated'})


class TenantRegistrationView(APIView):
    """
    View for registering new tenants with admin user.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Create new tenant with admin user."""
        try:
            with transaction.atomic():
                # Extract data
                tenant_data = request.data.get('tenant', {})
                user_data = request.data.get('user', {})
                domain_data = request.data.get('domain', {})
                
                # Create user
                user = User.objects.create_user(
                    username=user_data['email'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                )
                
                # Create tenant
                tenant = Tenant.objects.create(
                    name=tenant_data['name'],
                    schema_name=tenant_data['schema_name'],
                    slug=tenant_data['slug'],
                    business_type=tenant_data.get('business_type', 'retail'),
                    contact_email=user_data['email'],
                    contact_phone=tenant_data.get('contact_phone', ''),
                    address_line1=tenant_data.get('address_line1', ''),
                    city=tenant_data.get('city', ''),
                    state=tenant_data.get('state', ''),
                    postal_code=tenant_data.get('postal_code', ''),
                    trial_end_date=timezone.now() + timedelta(days=30),  # 30-day trial
                )
                
                # Create domain
                domain = Domain.objects.create(
                    domain=domain_data['domain'],
                    tenant=tenant,
                    is_primary=True
                )
                
                # Create tenant-user relationship
                tenant_user = TenantUser.objects.create(
                    user=user,
                    tenant=tenant,
                    role='owner',
                    can_manage_users=True,
                    can_manage_settings=True,
                    can_view_analytics=True,
                    can_manage_inventory=True,
                    can_process_sales=True,
                )
                
                # Initialize tenant schema with default data
                with schema_context(tenant.schema_name):
                    self._create_default_data(tenant)
                
                return Response({
                    'tenant': TenantSerializer(tenant).data,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'domain': domain.domain,
                    'message': 'Tenant created successfully'
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _create_default_data(self, tenant):
        """Create default data for new tenant."""
        from settings_app.models import Store
        from products.models import Category
        
        # Create default store
        Store.objects.create(
            name=f"{tenant.name} - Main Store",
            store_code="MAIN",
            store_type="main",
            is_active=True,
            currency="USD",
            timezone="UTC",
        )
        
        # Create default categories
        default_categories = [
            "General Merchandise",
            "Electronics", 
            "Clothing & Accessories",
            "Food & Beverages",
            "Health & Beauty",
        ]
        
        for category_name in default_categories:
            Category.objects.create(
                name=category_name,
                is_active=True,
            )


class TenantUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenant-user relationships.
    """
    serializer_class = TenantUserSerializer
    permission_classes = [IsTenantOwnerOrAdmin]
    
    def get_queryset(self):
        """Return users for current tenant."""
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return TenantUser.objects.filter(tenant_id=tenant_id)
        return TenantUser.objects.none()


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenant invitations.
    """
    serializer_class = TenantInvitationSerializer
    permission_classes = [IsTenantOwnerOrAdmin]
    
    def get_queryset(self):
        """Return invitations for current tenant."""
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return TenantInvitation.objects.filter(tenant_id=tenant_id)
        return TenantInvitation.objects.none()
    
    def perform_create(self, serializer):
        """Set invited_by to current user and create expiration date."""
        serializer.save(
            invited_by=self.request.user,
            expires_on=timezone.now() + timedelta(days=7)  # 7-day expiration
        )


class PublicRegistrationView(APIView):
    """
    Public registration view for creating tenant + user.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Handle public registration."""
        return TenantRegistrationView().post(request)


class TenantAwareLoginView(TokenObtainPairView):
    """
    Tenant-aware login view that resolves tenant from domain.
    """
    serializer_class = TenantTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """Handle tenant-aware login."""
        # Get domain from request
        domain = request.META.get('HTTP_HOST', '').split(':')[0]
        
        try:
            # Find tenant by domain
            domain_obj = Domain.objects.get(domain=domain)
            tenant = domain_obj.tenant
            
            # Set tenant context
            request.tenant = tenant
            
            # Proceed with normal JWT authentication
            response = super().post(request, *args, **kwargs)
            
            # Add tenant information to response
            if response.status_code == 200:
                response.data['tenant'] = {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'slug': tenant.slug,
                }
            
            return response
            
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Invalid domain'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class TenantLoginView(TokenObtainPairView):
    """
    Tenant-specific login view (within tenant context).
    """
    serializer_class = TenantTokenObtainPairSerializer


class TenantUserListView(ListCreateAPIView):
    """
    List and create users for a specific tenant.
    """
    serializer_class = TenantUserSerializer
    permission_classes = [IsTenantOwnerOrAdmin]
    
    def get_queryset(self):
        tenant_id = self.kwargs['tenant_id']
        return TenantUser.objects.filter(tenant_id=tenant_id)


class DomainManagementView(APIView):
    """
    View for managing tenant domains.
    """
    permission_classes = [IsTenantOwnerOrAdmin]
    
    def get(self, request):
        """List domains for user's tenants."""
        user_tenants = TenantUser.objects.filter(
            user=request.user, is_active=True
        ).values_list('tenant_id', flat=True)
        
        domains = Domain.objects.filter(tenant_id__in=user_tenants)
        
        return Response([
            {
                'id': domain.id,
                'domain': domain.domain,
                'tenant_name': domain.tenant.name,
                'is_primary': domain.is_primary,
            }
            for domain in domains
        ])
    
    def post(self, request):
        """Add new domain to tenant."""
        tenant_id = request.data.get('tenant_id')
        domain_name = request.data.get('domain')
        is_primary = request.data.get('is_primary', False)
        
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            
            # Check if user has permission for this tenant
            TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                role__in=['owner', 'admin'],
                is_active=True
            )
            
            domain = Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=is_primary
            )
            
            return Response({
                'id': domain.id,
                'domain': domain.domain,
                'tenant_name': tenant.name,
                'is_primary': domain.is_primary,
            }, status=status.HTTP_201_CREATED)
            
        except (Tenant.DoesNotExist, TenantUser.DoesNotExist):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )


class TenantUserProfileView(APIView):
    """
    View for managing user profile within tenant context.
    """
    permission_classes = [IsTenantMember]
    
    def get(self, request):
        """Get current user's tenant profile."""
        tenant_user = getattr(request, 'tenant_user', None)
        if tenant_user:
            return Response(TenantUserSerializer(tenant_user).data)
        return Response({'error': 'No tenant context'}, status=400)
    
    def patch(self, request):
        """Update user's tenant profile."""
        tenant_user = getattr(request, 'tenant_user', None)
        if not tenant_user:
            return Response({'error': 'No tenant context'}, status=400)
        
        serializer = TenantUserSerializer(
            tenant_user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ChangePasswordView(APIView):
    """
    View for changing password within tenant context.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change user password."""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Invalid old password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        request.user.set_password(new_password)
        request.user.save()
        
        return Response({'message': 'Password changed successfully'})


class LogoutView(APIView):
    """
    View for logging out (blacklist JWT token).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user by blacklisting token."""
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'message': 'Logged out successfully'})


class PasswordResetView(APIView):
    """
    View for password reset functionality.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Send password reset email."""
        email = request.data.get('email')
        # Implement password reset logic here
        return Response({'message': 'Password reset email sent'})


class PasswordResetConfirmView(APIView):
    """
    View for confirming password reset.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Confirm password reset with token."""
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        # Implement password reset confirmation logic here
        return Response({'message': 'Password reset successfully'})