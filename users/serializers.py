# Django Import
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, UserActivity, UserSession

from tenants.models import TenantUser

# Python Import


class UserSerializer(serializers.ModelSerializer):

    role = serializers.CharField(source='profile.get_role_display', read_only=True) # Display user role

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'date_joined', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login', 'role') # role is read-only here, managed via


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    email = serializers.EmailField(required=True, allow_blank=False) # Email required, not blank
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True) # 'first_name' optional
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True) # 'last_name' optional
    role = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name','role')
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}, # Redundant min_length, but for clarity
            'password2': {'write_only': True, 'min_length': 8}, # Redundant min_length, but for clarity
            'username': {'min_length': 3, 'max_length': 150}, # Username min/max length
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        role = validated_data.pop('role')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name') or '',  # Use empty string if not provided
            last_name=validated_data.get('last_name') or '',    # Use empty string if not provided
            password=validated_data['password']
        )
        # Create UserProfile automatically after user creation (optional, can also be done via signals)
        UserProfile.objects.create(user=user, role=role)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    
    username = serializers.CharField(source='user.username', read_only=True) # Display username from related User
    email = serializers.EmailField(source='user.email', read_only=True) # Display email from related User
    first_name = serializers.CharField(source='user.first_name', required=False) # Display first_name from related User
    last_name = serializers.CharField(source='user.last_name', required=False) # Display last_name from related User
    role = serializers.CharField(required=False) # Role is optional for profile updates (or make it required based on your logic)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'username', 'email', 'first_name', 'last_name', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'username', 'email'] # user and user details are read-only here

    def update(self, instance, validated_data):
        # Pop user data from the validated_data.
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update the related user's first_name and last_name if provided.
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.save()

        # Update the profile instance with any remaining validated_data.
        return super().update(instance, validated_data)


class TenantUserProfileSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for tenant-specific user profiles.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    full_name = serializers.SerializerMethodField()
    
    # Tenant-specific fields
    tenant_role = serializers.SerializerMethodField()
    tenant_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'tenant_role', 'tenant_permissions', 'department', 'employee_id', 
            'phone_number', 'can_access_pos', 'can_view_reports', 'can_manage_products',
            'can_manage_customers', 'can_process_returns', 'can_manage_discounts',
            'is_active', 'last_login_tenant', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'username', 'email', 'full_name', 'tenant_role', 
            'tenant_permissions', 'last_login_tenant', 'created_at', 'updated_at'
        ]
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_tenant_role(self, obj):
        """Get user's role in current tenant from TenantUser model."""
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            try:
                tenant_user = TenantUser.objects.get(
                    user=obj.user, 
                    tenant=request.tenant,
                    is_active=True
                )
                return tenant_user.role
            except TenantUser.DoesNotExist:
                pass
        return None
    
    def get_tenant_permissions(self, obj):
        """Get user's permissions in current tenant."""
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            try:
                tenant_user = TenantUser.objects.get(
                    user=obj.user, 
                    tenant=request.tenant,
                    is_active=True
                )
                return {
                    'can_manage_users': tenant_user.can_manage_users,
                    'can_manage_settings': tenant_user.can_manage_settings,
                    'can_view_analytics': tenant_user.can_view_analytics,
                    'can_manage_inventory': tenant_user.can_manage_inventory,
                    'can_process_sales': tenant_user.can_process_sales,
                }
            except TenantUser.DoesNotExist:
                pass
        return {}
    
    def update(self, instance, validated_data):
        # Pop user data from the validated_data
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update the related user's first_name and last_name if provided
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.save()

        # Update the profile instance with any remaining validated_data
        return super().update(instance, validated_data)


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for user activity logs.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'username', 'user_full_name', 'action', 'action_display',
            'resource', 'resource_id', 'details', 'ip_address', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class TenantUserManagementSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and managing users within tenant context.
    """
    # User fields
    user_data = serializers.DictField(write_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    # Tenant relationship
    tenant_role = serializers.SerializerMethodField()
    tenant_status = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user_data', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'tenant_role', 'tenant_status', 'department', 'employee_id', 
            'phone_number', 'can_access_pos', 'can_view_reports', 'can_manage_products',
            'can_manage_customers', 'can_process_returns', 'can_manage_discounts',
            'is_active', 'created_at'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'tenant_role', 'tenant_status', 'created_at'
        ]
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_tenant_role(self, obj):
        """Get user's role in current tenant."""
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            try:
                tenant_user = TenantUser.objects.get(
                    user=obj.user, 
                    tenant=request.tenant
                )
                return tenant_user.role
            except TenantUser.DoesNotExist:
                pass
        return None
    
    def get_tenant_status(self, obj):
        """Get user's status in current tenant."""
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            try:
                tenant_user = TenantUser.objects.get(
                    user=obj.user, 
                    tenant=request.tenant
                )
                return {
                    'is_active': tenant_user.is_active,
                    'joined_on': tenant_user.joined_on,
                }
            except TenantUser.DoesNotExist:
                pass
        return {}
    
    def create(self, validated_data):
        """Create user and profile within tenant context."""
        user_data = validated_data.pop('user_data')
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            raise serializers.ValidationError("Tenant context required")
        
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
            role=validated_data.get('role', 'staff'),
            is_active=True
        )
        
        # Create user profile
        validated_data['user'] = user
        return super().create(validated_data)


class UserInvitationSerializer(serializers.Serializer):
    """
    Serializer for inviting users to join tenant.
    """
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_email(self, value):
        """Check if user already exists in tenant."""
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        if tenant:
            # Check if user already belongs to this tenant
            try:
                user = User.objects.get(email=value)
                if TenantUser.objects.filter(user=user, tenant=tenant, is_active=True).exists():
                    raise serializers.ValidationError("User already belongs to this tenant")
            except User.DoesNotExist:
                pass  # User doesn't exist, which is fine for invitation
        
        return value


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics within tenant.
    """
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    users_by_role = serializers.DictField()
    recent_logins = serializers.IntegerField()
    pending_invitations = serializers.IntegerField()