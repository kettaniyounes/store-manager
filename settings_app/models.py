# Django Imports
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError

# Python Imports
from decimal import Decimal


class Store(models.Model):
    """Model representing individual store locations"""
    
    STORE_TYPES = [
        ('main', 'Main Store'),
        ('branch', 'Branch Store'),
        ('warehouse', 'Warehouse'),
        ('online', 'Online Store'),
        ('kiosk', 'Kiosk'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Store Name',
        help_text='Name of the store location'
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Store Code',
        help_text='Unique code for the store (e.g., MAIN, BR01, WH01)'
    )
    store_type = models.CharField(
        max_length=20,
        choices=STORE_TYPES,
        default='branch',
        verbose_name='Store Type'
    )
    address = models.TextField(
        verbose_name='Address',
        help_text='Physical address of the store'
    )
    city = models.CharField(
        max_length=100,
        verbose_name='City'
    )
    state_province = models.CharField(
        max_length=100,
        verbose_name='State/Province'
    )
    postal_code = models.CharField(
        max_length=20,
        verbose_name='Postal Code'
    )
    country = models.CharField(
        max_length=100,
        verbose_name='Country'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Phone Number'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email Address'
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_stores',
        verbose_name='Store Manager'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Indicates if the store is currently operational'
    )
    is_main_store = models.BooleanField(
        default=False,
        verbose_name='Is Main Store',
        help_text='Indicates if this is the main/headquarters store'
    )
    opening_hours = models.JSONField(
        default=dict,
        verbose_name='Opening Hours',
        help_text='Store opening hours in JSON format'
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        verbose_name='Timezone',
        help_text='Store timezone (e.g., America/New_York)'
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name='Currency',
        help_text='Default currency for this store'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Default Tax Rate (%)',
        help_text='Default tax rate for this store'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code'], name='store_code_idx'),
            models.Index(fields=['is_active', 'store_type'], name='store_active_type_idx'),
        ]

    def clean(self):
        # Ensure only one main store exists
        if self.is_main_store:
            existing_main = Store.objects.filter(is_main_store=True).exclude(pk=self.pk)
            if existing_main.exists():
                raise ValidationError("Only one main store can exist.")

    def __str__(self):
        return f"{self.name} ({self.code})"


class StoreTransfer(models.Model):
    """Model for tracking inventory transfers between stores"""
    
    TRANSFER_STATUS = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    transfer_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Transfer Number',
        help_text='Unique transfer identifier'
    )
    from_store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='outgoing_transfers',
        verbose_name='From Store'
    )
    to_store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='incoming_transfers',
        verbose_name='To Store'
    )
    status = models.CharField(
        max_length=20,
        choices=TRANSFER_STATUS,
        default='pending',
        verbose_name='Status'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_transfers',
        verbose_name='Requested By'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transfers',
        verbose_name='Approved By'
    )
    shipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipped_transfers',
        verbose_name='Shipped By'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers',
        verbose_name='Received By'
    )
    request_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Request Date'
    )
    shipped_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Shipped Date'
    )
    received_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Received Date'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Additional notes about the transfer'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Transfer'
        verbose_name_plural = 'Store Transfers'
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['from_store', 'status'], name='transfer_from_status_idx'),
            models.Index(fields=['to_store', 'status'], name='transfer_to_status_idx'),
            models.Index(fields=['request_date'], name='transfer_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            # Auto-generate transfer number
            prefix = 'TRF'
            last_transfer = StoreTransfer.objects.order_by('-id').first()
            if last_transfer:
                last_number = last_transfer.transfer_number
                if last_number.startswith(prefix) and last_number[len(prefix):].isdigit():
                    next_number = int(last_number[len(prefix):]) + 1
                    self.transfer_number = f"{prefix}{next_number:06d}"
                else:
                    self.transfer_number = f"{prefix}000001"
            else:
                self.transfer_number = f"{prefix}000001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.transfer_number}: {self.from_store.code} → {self.to_store.code}"


class StoreTransferItem(models.Model):
    """Individual items in a store transfer"""
    
    transfer = models.ForeignKey(
        StoreTransfer,
        on_delete=models.CASCADE,
        related_name='transfer_items',
        verbose_name='Transfer'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Product Variant'
    )
    quantity_requested = models.IntegerField(
        verbose_name='Quantity Requested',
        help_text='Quantity requested for transfer'
    )
    quantity_shipped = models.IntegerField(
        default=0,
        verbose_name='Quantity Shipped',
        help_text='Actual quantity shipped'
    )
    quantity_received = models.IntegerField(
        default=0,
        verbose_name='Quantity Received',
        help_text='Actual quantity received'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost',
        help_text='Cost per unit for valuation'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Notes specific to this item'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Transfer Item'
        verbose_name_plural = 'Store Transfer Items'

    def __str__(self):
        return f"{self.product.name} - {self.quantity_requested} units"


class StoreSetting(models.Model):

    KEY_CHOICES = [
        # Define choices for setting keys (you can expand this list)
        ('store_name', 'Store Name'),
        ('default_currency', 'Default Currency'),
        ('tax_rate', 'Default Tax Rate (%)'),
        ('receipt_header', 'Receipt Header Text'),
        ('receipt_footer', 'Receipt Footer Text'),
        ('low_stock_alert', 'Low Stock Alert Enabled'),
        ('auto_reorder', 'Auto Reorder Enabled'),
        ('multi_store_mode', 'Multi-Store Mode Enabled'),
        # Add more setting keys as needed
    ]

    DATA_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('decimal', 'Decimal'),
        ('json', 'JSON'),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='settings',
        verbose_name='Store',
        help_text='Store this setting applies to (null for global settings)'
    )
    key = models.CharField(
        max_length=255,
        choices=KEY_CHOICES,
        verbose_name='Setting Key',
    )
    value = models.TextField(
        verbose_name='Setting Value',
        help_text='Value of the setting. Data type depends on the setting key.',
    )
    data_type = models.CharField(
        max_length=50,
        choices=DATA_TYPE_CHOICES,
        default='string',
        verbose_name='Data Type',
        help_text='Data type of the setting value',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description of what this setting controls (optional)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Setting'
        verbose_name_plural = 'Store Settings'
        ordering = ['store', 'key']  # Order settings by store and key
        unique_together = ('store', 'key')  # Ensure unique settings per store

    def __str__(self):
        store_name = self.store.name if self.store else "Global"
        return f"{store_name} - {self.get_key_display()}: {self.value}"  # Use get_key_display for user-friendly key name