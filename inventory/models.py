# Django Imports
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from django.utils import timezone
from django.core.exceptions import ValidationError

# Python Imports
from decimal import Decimal
import uuid


class StoreInventory(models.Model):
    """Track inventory levels per store location"""
    
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='inventory',
        verbose_name='Store'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='store_inventory',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='store_inventory',
        verbose_name='Product Variant'
    )
    quantity_on_hand = models.IntegerField(
        default=0,
        verbose_name='Quantity on Hand',
        help_text='Current stock quantity at this location'
    )
    quantity_reserved = models.IntegerField(
        default=0,
        verbose_name='Quantity Reserved',
        help_text='Quantity reserved for pending orders/transfers'
    )
    quantity_available = models.IntegerField(
        default=0,
        verbose_name='Quantity Available',
        help_text='Available quantity (on hand - reserved)'
    )
    reorder_point = models.IntegerField(
        default=0,
        verbose_name='Reorder Point',
        help_text='Store-specific reorder point'
    )
    max_stock_level = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Maximum Stock Level',
        help_text='Maximum stock level for this location'
    )
    average_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Cost',
        help_text='Weighted average cost at this location'
    )
    last_counted_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Counted Date',
        help_text='Date of last physical inventory count'
    )
    last_movement_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Movement Date',
        help_text='Date of last stock movement'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Inventory'
        verbose_name_plural = 'Store Inventories'
        unique_together = ('store', 'product', 'product_variant')
        ordering = ['store', 'product']
        indexes = [
            models.Index(fields=['store', 'quantity_on_hand'], name='store_inventory_qty_idx'),
            models.Index(fields=['product', 'store'], name='product_store_idx'),
            models.Index(fields=['quantity_on_hand', 'reorder_point'], name='reorder_check_idx'),
        ]

    def save(self, *args, **kwargs):
        # Calculate available quantity
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)

    def is_low_stock(self):
        """Check if inventory is below reorder point"""
        return self.quantity_available <= self.reorder_point

    def needs_reorder(self):
        """Check if inventory needs reordering"""
        return self.quantity_available <= self.reorder_point

    def __str__(self):
        variant_info = f" - {self.product_variant}" if self.product_variant else ""
        return f"{self.store.name}: {self.product.name}{variant_info} ({self.quantity_on_hand} units)"


class StoreStockMovement(models.Model):
    """Track all stock movements per store location"""
    
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase/Stock In'),
        ('sale', 'Sale/Stock Out'),
        ('adjustment', 'Stock Adjustment'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('return', 'Customer Return'),
        ('damage', 'Damage/Loss'),
        ('expired', 'Expired Product'),
        ('count', 'Physical Count Adjustment'),
    ]
    
    movement_id = models.CharField(
        max_length=50,
        unique=True,
        default=uuid.uuid4,
        verbose_name='Movement ID'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='inventory_stock_movements',
        verbose_name='Store'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='store_stock_movements',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='store_stock_movements',
        verbose_name='Product Variant'
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES,
        verbose_name='Movement Type'
    )
    quantity = models.IntegerField(
        verbose_name='Quantity',
        help_text='Positive for stock in, negative for stock out'
    )
    quantity_before = models.IntegerField(
        verbose_name='Quantity Before',
        help_text='Stock quantity before this movement'
    )
    quantity_after = models.IntegerField(
        verbose_name='Quantity After',
        help_text='Stock quantity after this movement'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total Cost'
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference ID',
        help_text='Reference to related transaction (Sale, Transfer, etc.)'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User'
    )
    movement_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Movement Date'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Stock Movement'
        verbose_name_plural = 'Store Stock Movements'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['store', 'movement_date'], name='inv_store_movement_date_idx'),
            models.Index(fields=['product', 'store', 'movement_date'], name='product_store_date_idx'),
            models.Index(fields=['movement_type', 'movement_date'], name='inv_movement_type_date_idx'),
        ]

    def save(self, *args, **kwargs):
        # Calculate total cost
        self.total_cost = abs(self.quantity) * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.store.code} - {self.movement_type}: {self.product.name} ({self.quantity} units)"


class StoreInventoryCount(models.Model):
    """Physical inventory count records per store"""
    
    COUNT_STATUS = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    count_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Count Number'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='inventory_counts',
        verbose_name='Store'
    )
    count_date = models.DateField(
        verbose_name='Count Date'
    )
    status = models.CharField(
        max_length=20,
        choices=COUNT_STATUS,
        default='planned',
        verbose_name='Status'
    )
    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_counts',
        verbose_name='Counted By'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_counts',
        verbose_name='Approved By'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Inventory Count'
        verbose_name_plural = 'Store Inventory Counts'
        ordering = ['-count_date']

    def save(self, *args, **kwargs):
        if not self.count_number:
            # Auto-generate count number
            prefix = f"CNT{self.store.code}"
            last_count = StoreInventoryCount.objects.filter(
                store=self.store
            ).order_by('-id').first()
            
            if last_count:
                last_number = last_count.count_number
                if last_number.startswith(prefix) and last_number[len(prefix):].isdigit():
                    next_number = int(last_number[len(prefix):]) + 1
                    self.count_number = f"{prefix}{next_number:04d}"
                else:
                    self.count_number = f"{prefix}0001"
            else:
                self.count_number = f"{prefix}0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Count {self.count_number} - {self.store.name} ({self.count_date})"


class StoreInventoryCountItem(models.Model):
    """Individual items in an inventory count"""
    
    count = models.ForeignKey(
        StoreInventoryCount,
        on_delete=models.CASCADE,
        related_name='count_items',
        verbose_name='Inventory Count'
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
    system_quantity = models.IntegerField(
        verbose_name='System Quantity',
        help_text='Quantity according to system records'
    )
    counted_quantity = models.IntegerField(
        verbose_name='Counted Quantity',
        help_text='Actual counted quantity'
    )
    variance = models.IntegerField(
        verbose_name='Variance',
        help_text='Difference between counted and system quantity'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost'
    )
    variance_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Variance Value',
        help_text='Financial impact of the variance'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Inventory Count Item'
        verbose_name_plural = 'Store Inventory Count Items'
        unique_together = ('count', 'product', 'product_variant')

    def save(self, *args, **kwargs):
        # Calculate variance and variance value
        self.variance = self.counted_quantity - self.system_quantity
        self.variance_value = self.variance * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        variant_info = f" - {self.product_variant}" if self.product_variant else ""
        return f"{self.product.name}{variant_info} (Variance: {self.variance})"


# Create alias for StoreInventory to match view expectations
LocationInventory = StoreInventory


class StoreTransfer(models.Model):
    """Track transfers between store locations"""
    
    TRANSFER_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    transfer_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Transfer Number'
    )
    from_store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='outbound_transfers',
        verbose_name='From Store'
    )
    to_store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='inbound_transfers',
        verbose_name='To Store'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transfers',
        verbose_name='Product Variant'
    )
    quantity = models.IntegerField(
        verbose_name='Quantity',
        help_text='Quantity to transfer'
    )
    status = models.CharField(
        max_length=20,
        choices=TRANSFER_STATUS,
        default='pending',
        verbose_name='Status'
    )
    transfer_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Transfer Date'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_requested_transfers',
        verbose_name='Requested By'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_approved_transfers',
        verbose_name='Approved By'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Approved At'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completed At'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Transfer'
        verbose_name_plural = 'Store Transfers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_store', 'to_store'], name='transfer_stores_idx'),
            models.Index(fields=['status', 'transfer_date'], name='transfer_status_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            # Auto-generate transfer number
            prefix = "TRF"
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

    def clean(self):
        if self.from_store == self.to_store:
            raise ValidationError("Source and destination stores cannot be the same.")

    def __str__(self):
        return f"Transfer {self.transfer_number}: {self.from_store.name} → {self.to_store.name}"


PhysicalCount = StoreInventoryCount


class PhysicalCountItem(models.Model):
    """Individual items in a physical count - alias for StoreInventoryCountItem"""
    
    count = models.ForeignKey(
        PhysicalCount,
        on_delete=models.CASCADE,
        related_name='physicalcountitem_set',
        verbose_name='Physical Count'
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
    system_quantity = models.IntegerField(
        verbose_name='System Quantity',
        help_text='Quantity according to system records'
    )
    counted_quantity = models.IntegerField(
        verbose_name='Counted Quantity',
        help_text='Actual counted quantity'
    )
    variance = models.IntegerField(
        verbose_name='Variance',
        help_text='Difference between counted and system quantity'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost'
    )
    variance_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Variance Value',
        help_text='Financial impact of the variance'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Physical Count Item'
        verbose_name_plural = 'Physical Count Items'
        unique_together = ('count', 'product', 'product_variant')

    def save(self, *args, **kwargs):
        # Calculate variance and variance value
        self.variance = self.counted_quantity - self.system_quantity
        self.variance_value = self.variance * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        variant_info = f" - {self.product_variant}" if self.product_variant else ""
        return f"{self.product.name}{variant_info} (Variance: {self.variance})"