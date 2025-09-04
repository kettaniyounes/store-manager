# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings

# Python Imports


class UserProfile(models.Model):
    """
    Extended user profile model for tenant-aware user management.
    Note: This model exists in tenant schemas, not public schema.
    The TenantUser model in the public schema handles tenant-user relationships.
    """

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('inventory', 'Inventory Staff'),
        ('cashier', 'Cashier'),
        ('viewer', 'Viewer'),
        # Add more roles as needed
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='User'
    ) # One-to-one link to Django User
    
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='staff',
        verbose_name='Role',
        help_text='User\'s role within this tenant'
    )
    
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text='Department or team within the organization'
    )
    
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        help_text='Employee ID or staff number'
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )
    
    # Permissions within tenant
    can_access_pos = models.BooleanField(
        default=True,
        help_text='Can access Point of Sale system'
    )
    
    can_view_reports = models.BooleanField(
        default=False,
        help_text='Can view business reports and analytics'
    )
    
    can_manage_products = models.BooleanField(
        default=False,
        help_text='Can add, edit, and delete products'
    )
    
    can_manage_customers = models.BooleanField(
        default=False,
        help_text='Can manage customer information'
    )
    
    can_process_returns = models.BooleanField(
        default=False,
        help_text='Can process returns and refunds'
    )
    
    can_manage_discounts = models.BooleanField(
        default=False,
        help_text='Can apply and manage discounts'
    )
    
    # Status and activity
    is_active = models.BooleanField(
        default=True,
        help_text='User is active within this tenant'
    )
    
    last_login_tenant = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last login time for this tenant'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile for {self.user.username} - Role: {self.get_role_display()}"
    
    @property
    def is_manager_or_above(self):
        """Check if user has manager level access or above."""
        return self.role in ['owner', 'manager']
    
    @property
    def can_manage_staff(self):
        """Check if user can manage other staff members."""
        return self.role in ['owner', 'manager'] and self.can_view_reports
    
    def has_permission(self, permission):
        """Check if user has specific permission."""
        permission_map = {
            'pos': self.can_access_pos,
            'reports': self.can_view_reports,
            'products': self.can_manage_products,
            'customers': self.can_manage_customers,
            'returns': self.can_process_returns,
            'discounts': self.can_manage_discounts,
        }
        return permission_map.get(permission, False)


class UserSession(models.Model):
    """
    Track user sessions within tenant context for security and analytics.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_sessions'
    )
    
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Session details
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class UserActivity(models.Model):
    """
    Log user activities within tenant for audit purposes.
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_activities'
    )
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource = models.CharField(max_length=100, help_text='What was acted upon')
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} {self.resource}"