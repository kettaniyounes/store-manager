# Django Import
from rest_framework import generics, permissions, status, viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.db import connection
from django.utils import timezone

from tenants.permissions import IsTenantMember, CanManageUsers, IsTenantOwnerOrAdmin
from tenants.models import TenantUser
from .models import UserProfile, UserSession, UserActivity
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserProfileSerializer,
    TenantUserProfileSerializer, UserActivitySerializer
)
from .permissions import IsAdminOrReadOnlyUser

# Python Import


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration view - now tenant-aware.
    Note: This should typically be handled by tenant registration flow.
    """
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny] # Allow anyone to register

    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {'error': 'Tenant context required for registration'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        UserProfile.objects.create(
            user=user,
            role=request.data.get('role', 'staff'),
            department=request.data.get('department', ''),
            employee_id=request.data.get('employee_id', ''),
        )
        
        refresh = RefreshToken.for_user(user)
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Tenant-aware user profile management.
    """
    
    serializer_class = TenantUserProfileSerializer
    permission_classes = [IsTenantMember] # Use tenant-aware permission
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'role': 'staff'}
        )
        return profile
    
    def perform_update(self, serializer):
        UserActivity.objects.create(
            user=self.request.user,
            action='update',
            resource='user_profile',
            resource_id=str(self.request.user.id),
            ip_address=self.get_client_ip(),
            details={'updated_fields': list(serializer.validated_data.keys())}
        )
        serializer.save()
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class TenantUserViewSet(viewsets.ModelViewSet):
    """
    Tenant-aware user management ViewSet.
    """

    serializer_class = TenantUserProfileSerializer
    permission_classes = [CanManageUsers] # Use tenant permission
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['user__username', 'user__date_joined', 'role']
    ordering = ['user__username']

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserProfile.objects.none()
        
        # Get users who belong to this tenant
        tenant_user_ids = TenantUser.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        
        return UserProfile.objects.filter(
            user_id__in=tenant_user_ids,
            is_active=True
        ).select_related('user')

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        user_data = self.request.data.get('user', {})
        
        # Create Django user
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
        )
        
        # Create tenant-user relationship
        TenantUser.objects.create(
            user=user,
            tenant=tenant,
            role=self.request.data.get('role', 'staff'),
            is_active=True
        )
        
        # Create tenant-specific profile
        serializer.save(user=user)
        
        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='create',
            resource='user',
            resource_id=str(user.id),
            ip_address=self.get_client_ip(),
            details={'created_user': user.username}
        )

    def perform_update(self, serializer):
        UserActivity.objects.create(
            user=self.request.user,
            action='update',
            resource='user',
            resource_id=str(serializer.instance.user.id),
            ip_address=self.get_client_ip(),
            details={'updated_user': serializer.instance.user.username}
        )
        serializer.save()
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        
        # Also deactivate tenant-user relationship
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            TenantUser.objects.filter(
                user=instance.user, tenant=tenant
            ).update(is_active=False)
        
        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='delete',
            resource='user',
            resource_id=str(instance.user.id),
            ip_address=self.get_client_ip(),
            details={'deactivated_user': instance.user.username}
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user."""
        user_profile = self.get_object()
        user_profile.is_active = True
        user_profile.save()
        
        # Also activate tenant-user relationship
        tenant = getattr(request, 'tenant', None)
        if tenant:
            TenantUser.objects.filter(
                user=user_profile.user, tenant=tenant
            ).update(is_active=True)
        
        return Response({'status': 'User activated'})
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password."""
        user_profile = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'New password required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_profile.user.set_password(new_password)
        user_profile.user.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            action='update',
            resource='user_password',
            resource_id=str(user_profile.user.id),
            ip_address=self.get_client_ip(),
            details={'password_reset_for': user_profile.user.username}
        )
        
        return Response({'status': 'Password reset successfully'})
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View user activities within tenant for audit purposes.
    """
    serializer_class = UserActivitySerializer
    permission_classes = [IsTenantOwnerOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'action', 'resource']
    ordering_fields = ['timestamp', 'action', 'user__username']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Return activities for current tenant users."""
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserActivity.objects.none()
        
        # Get users who belong to this tenant
        tenant_user_ids = TenantUser.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        
        return UserActivity.objects.filter(
            user_id__in=tenant_user_ids
        ).select_related('user')


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View active user sessions within tenant.
    """
    permission_classes = [IsTenantOwnerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['login_time', 'last_activity']
    ordering = ['-last_activity']
    
    def get_queryset(self):
        """Return active sessions for current tenant users."""
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserSession.objects.none()
        
        # Get users who belong to this tenant
        tenant_user_ids = TenantUser.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        
        return UserSession.objects.filter(
            user_id__in=tenant_user_ids,
            is_active=True
        ).select_related('user')
    
    def get_serializer_class(self):
        # Simple serializer for session data
        from rest_framework import serializers
        
        class UserSessionSerializer(serializers.ModelSerializer):
            username = serializers.CharField(source='user.username', read_only=True)
            
            class Meta:
                model = UserSession
                fields = ['id', 'username', 'ip_address', 'login_time', 'last_activity']
        
        return UserSessionSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    Legacy user management ViewSet - now tenant-aware.
    """

    serializer_class = UserSerializer
    permission_classes = [CanManageUsers] # Use tenant permission
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined', 'last_login']
    ordering = ['username']

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return User.objects.none()
        
        # Get users who belong to this tenant
        tenant_user_ids = TenantUser.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        
        return User.objects.filter(id__in=tenant_user_ids).order_by('username')

    def perform_create(self, serializer):
        return Response(
            {'error': 'Use tenant user management endpoints for user creation'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    def perform_update(self, serializer):
        if not self.request.user.is_superuser and 'is_superuser' in serializer.validated_data:
            serializer.validated_data.pop('is_superuser')
        serializer.save()