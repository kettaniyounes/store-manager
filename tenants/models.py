from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import uuid


class Tenant(TenantMixin):
    """
    Tenant model for schema-based multi-tenancy.
    Each tenant gets its own PostgreSQL schema for complete data isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Business/Company name")
    slug = models.SlugField(max_length=50, unique=True, help_text="URL-friendly identifier")
    
    # Business information
    business_type = models.CharField(
        max_length=50,
        choices=[
            ('retail', 'Retail Store'),
            ('restaurant', 'Restaurant'),
            ('pharmacy', 'Pharmacy'),
            ('grocery', 'Grocery Store'),
            ('electronics', 'Electronics Store'),
            ('clothing', 'Clothing Store'),
            ('other', 'Other'),
        ],
        default='retail'
    )
    
    # Contact information
    contact_email = models.EmailField()
    contact_phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    
    # Address information
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    
    # Subscription and status
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Trial'),
            ('basic', 'Basic'),
            ('premium', 'Premium'),
            ('enterprise', 'Enterprise'),
        ],
        default='trial'
    )
    
    is_active = models.BooleanField(default=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')
    
    # Auto-generated fields required by django-tenants
    auto_create_schema = True
    auto_drop_schema = True
    
    class Meta:
        db_table = 'tenants_tenant'
        
    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Domain model for tenant routing.
    Maps domains/subdomains to specific tenants.
    """
    pass


class TenantUser(models.Model):
    """
    Junction model linking global users to specific tenants with roles.
    Allows users to belong to multiple tenants with different permissions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='user_memberships')
    
    # Role within the tenant
    role = models.CharField(
        max_length=50,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Administrator'),
            ('manager', 'Manager'),
            ('staff', 'Staff'),
            ('viewer', 'Viewer'),
        ],
        default='staff'
    )
    
    # Status and permissions
    is_active = models.BooleanField(default=True)
    can_manage_users = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=True)
    can_manage_inventory = models.BooleanField(default=False)
    can_process_sales = models.BooleanField(default=True)
    
    # Timestamps
    joined_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'tenant')
        db_table = 'tenant_users'
        
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.role})"
    
    @property
    def is_owner_or_admin(self):
        return self.role in ['owner', 'admin']
    
    @property
    def can_manage_tenant(self):
        return self.role in ['owner', 'admin'] and self.can_manage_settings


class TenantInvitation(models.Model):
    """
    Model for managing tenant invitations to new users.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    
    # Invitation details
    email = models.EmailField()
    role = models.CharField(
        max_length=50,
        choices=[
            ('admin', 'Administrator'),
            ('manager', 'Manager'),
            ('staff', 'Staff'),
            ('viewer', 'Viewer'),
        ],
        default='staff'
    )
    
    # Invitation status
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_accepted = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    
    # Timestamps
    created_on = models.DateTimeField(auto_now_add=True)
    expires_on = models.DateTimeField()
    accepted_on = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('tenant', 'email')
        db_table = 'tenant_invitations'
        
    def __str__(self):
        return f"Invitation to {self.email} for {self.tenant.name}"