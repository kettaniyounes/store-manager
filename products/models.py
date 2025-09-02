# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

# Python Imports
from decimal import Decimal
import uuid

# Local Imports
from settings_app.models import Store
from settings_app.base_models import TenantAwareHistoricalModel, SharedReferenceModel, tenant_aware_unique_together


class Category(SharedReferenceModel):
    """Shared reference model - categories are global across all tenants"""

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Category Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Optional description for the category'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()  # Enable audit trail for Category

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name
    



class Brand(SharedReferenceModel):
    """Shared reference model - brands are global across all tenants"""

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Brand Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Optional description for the brand'
    )
    logo = models.ImageField(
        upload_to='brand_logos/',
        blank=True,
        verbose_name='Logo',
        help_text='Optional brand logo image'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']

    def __str__(self):
        return self.name
    



@tenant_aware_unique_together('sku')
@tenant_aware_unique_together('barcode')
class Product(TenantAwareHistoricalModel):
    """Tenant-aware product model - products are isolated per tenant"""

    _tenant_field = 'default_store__tenant'

    name = models.CharField(
        max_length=255,
        verbose_name='Product Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Detailed product description'
    )
    sku = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='SKU',
        help_text='Stock Keeping Unit - unique product identifier'
    )
    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Barcode',
        help_text='Optional barcode for product scanning'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Category',
        help_text='Category of the product'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Brand',
        help_text='Optional brand of the product',
    ) 
    default_store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='default_products',
        verbose_name='Default Store',
        help_text='Default store location for this product'
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Cost Price',
        help_text='Cost price of the product'
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Selling Price',
        help_text='Selling price of the product'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Tax Rate (%)',
        help_text='Tax rate for the product as percentage'
    )
    unit_of_measurement = models.CharField(
        max_length=50,
        default='pieces',
        verbose_name='Unit of Measurement',
        help_text='Unit in which product is measured (e.g., pieces, kg, liters)'
    )
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name='Stock Quantity (Legacy)',
        help_text='Legacy field - use LocationInventory for multi-store support'
    )
    low_stock_threshold = models.IntegerField(
        default=10,
        verbose_name='Low Stock Threshold',
        help_text='Quantity below which low stock alerts are triggered'
    )
    reorder_point = models.IntegerField(
        default=20,
        verbose_name='Reorder Point',
        help_text='Stock level at which automatic reorder should be triggered'
    )
    reorder_quantity = models.IntegerField(
        default=50,
        verbose_name='Reorder Quantity',
        help_text='Quantity to order when reorder point is reached'
    )
    maximum_stock_level = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Maximum Stock Level',
        help_text='Maximum stock level to maintain (optional)'
    )
    inventory_valuation_method = models.CharField(
        max_length=20,
        choices=[
            ('fifo', 'First In, First Out (FIFO)'),
            ('lifo', 'Last In, First Out (LIFO)'),
            ('average', 'Weighted Average Cost'),
        ],
        default='fifo',
        verbose_name='Inventory Valuation Method',
        help_text='Method used for inventory cost calculation'
    )
    is_perishable = models.BooleanField(
        default=False,
        verbose_name='Is Perishable',
        help_text='Indicates if the product has expiration dates'
    )
    shelf_life_days = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Shelf Life (Days)',
        help_text='Number of days product remains fresh (for perishable items)'
    )
    average_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Cost',
        help_text='Weighted average cost of inventory (calculated automatically)'
    )
    total_inventory_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Inventory Value',
        help_text='Total value of current inventory (calculated automatically)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Indicates if the product is active and available for sale'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category', 'selling_price'], name='category_price_idx'),
            models.Index(fields=['stock_quantity', 'reorder_point'], name='stock_reorder_idx'),
            models.Index(fields=['is_perishable', 'shelf_life_days'], name='perishable_idx'),
            models.Index(fields=['default_store', 'is_active'], name='store_active_idx'),
            models.Index(fields=['default_store__tenant', 'sku'], name='tenant_sku_idx'),
            models.Index(fields=['default_store__tenant', 'barcode'], name='tenant_barcode_idx'),
            models.Index(fields=['default_store__tenant', 'is_active'], name='tenant_active_idx'),
        ]
    
    def clean(self):
        super().clean()
        # Validate that selling price is not less than cost price
        if self.selling_price < self.cost_price:
            raise ValidationError("Selling price cannot be less than cost price.")
        
        if self.reorder_point >= self.reorder_quantity:
            raise ValidationError("Reorder point should be less than reorder quantity.")
        
        if self.maximum_stock_level and self.maximum_stock_level <= self.reorder_point:
            raise ValidationError("Maximum stock level should be greater than reorder point.")
        
        if self.is_perishable and not self.shelf_life_days:
            raise ValidationError("Shelf life days is required for perishable products.")

    def is_low_stock(self):
        """Check if product is below low stock threshold"""
        return self.stock_quantity <= self.low_stock_threshold
    
    def needs_reorder(self):
        """Check if product needs to be reordered"""
        return self.stock_quantity <= self.reorder_point
    
    def profit_margin_percentage(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return Decimal('0.00')
    
    def profit_per_unit(self):
        """Calculate profit per unit"""
        return self.selling_price - self.cost_price
    
    def update_inventory_value(self):
        """Update total inventory value based on current stock and average cost"""
        self.total_inventory_value = self.stock_quantity * self.average_cost
        self.save(update_fields=['total_inventory_value'])

    def get_total_stock_across_stores(self):
        """Get total stock quantity across all store locations"""
        from inventory.models import LocationInventory
        total = LocationInventory.objects.filter(product=self).aggregate(
            total_stock=models.Sum('quantity_on_hand')
        )['total_stock']
        return total or 0
    
    def get_stock_by_store(self, store):
        """Get stock quantity for a specific store"""
        from inventory.models import LocationInventory
        try:
            location_inventory = LocationInventory.objects.get(product=self, store=store)
            return location_inventory.quantity_on_hand
        except LocationInventory.DoesNotExist:
            return 0

    def get_available_stock_by_store(self, store):
        """Get available stock quantity for a specific store (on hand - reserved)"""
        from inventory.models import LocationInventory
        try:
            location_inventory = LocationInventory.objects.get(product=self, store=store)
            return location_inventory.quantity_available
        except LocationInventory.DoesNotExist:
            return 0

    def get_stores_with_stock(self):
        """Get list of stores that have this product in stock"""
        from inventory.models import LocationInventory
        return LocationInventory.objects.filter(
            product=self, 
            quantity_on_hand__gt=0
        ).select_related('store').values_list('store', flat=True)

    def is_low_stock_at_store(self, store):
        """Check if product is below low stock threshold at a specific store"""
        stock = self.get_stock_by_store(store)
        return stock <= self.low_stock_threshold

    def needs_reorder_at_store(self, store):
        """Check if product needs reordering at a specific store"""
        from inventory.models import LocationInventory
        try:
            location_inventory = LocationInventory.objects.get(product=self, store=store)
            return location_inventory.quantity_available <= location_inventory.reorder_point
        except LocationInventory.DoesNotExist:
            return True  # If no inventory record exists, it needs to be ordered

    def get_total_sales_by_store(self, store, days=30):
        """Get total sales quantity for this product at a specific store in the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        total_sales = self.sale_items.filter(
            store=store,
            created_at__gte=start_date,
            sale_transaction__status='completed'
        ).aggregate(
            total_quantity=models.Sum('quantity')
        )['total_quantity']
        return total_sales or 0

    def __str__(self):
        return self.name


class ProductImage(TenantAwareHistoricalModel):
    """Tenant-aware product image model"""
    
    _tenant_field = 'product__default_store__tenant'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Product',
        help_text='Related product'
    ) # related_name for reverse relation
    image = models.ImageField(
        upload_to='product_images/',
        verbose_name='Image',
        help_text='Product image file'
    ) # Store product images in 'product_images/' media subdirectory
    is_thumbnail = models.BooleanField(
        default=False,
        verbose_name='Is Thumbnail',
        help_text='Indicates if this image is the thumbnail for the product'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"Image for {self.product.name} (ID: {self.id})"
    



@tenant_aware_unique_together('product', 'name', 'value')
class ProductVariant(TenantAwareHistoricalModel):
    """Tenant-aware product variant model"""
    
    _tenant_field = 'product__default_store__tenant'
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Product',
        help_text='Parent product'
    ) # related_name for reverse relation
    name = models.CharField(
        max_length=255,
        verbose_name='Variant Option Name',
        help_text='Name of the variant option (e.g., Size, Color)'
    )
    value = models.CharField(
        max_length=255,
        verbose_name='Variant Value',
        help_text='Value of the variant option (e.g., Large, Red)'
    )
    additional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Additional Price',
        help_text='Additional price for this variant (can be positive or negative)'
    )
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name='Variant Stock Quantity',
        help_text='Stock quantity specific to this variant'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        ordering = ['name', 'value']

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}" # More informative __str__


@tenant_aware_unique_together('movement_id')
class StockMovement(TenantAwareHistoricalModel):
    """Tenant-aware stock movement tracking"""
    
    _tenant_field = 'store__tenant'
    
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
        default=uuid.uuid4,
        verbose_name='Movement ID',
        help_text='Unique identifier for this stock movement'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Product Variant'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='Store Location',
        help_text='Store location where this movement occurred'
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
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost',
        help_text='Cost per unit for this movement'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total Cost',
        help_text='Total cost of this movement (quantity × unit cost)'
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference ID',
        help_text='Reference to related transaction (PO, Sale, etc.)'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Additional notes about this stock movement'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User',
        help_text='User who performed this stock movement'
    )
    movement_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Movement Date'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['product', 'movement_date'], name='product_movement_date_idx'),
            models.Index(fields=['movement_type', 'movement_date'], name='movement_type_date_idx'),
            models.Index(fields=['store', 'movement_date'], name='store_movement_date_idx'),
            models.Index(fields=['store', 'product'], name='store_product_idx'),
            models.Index(fields=['store__tenant', 'movement_date'], name='tenant_movement_date_idx'),
            models.Index(fields=['store__tenant', 'product'], name='tenant_product_movement_idx'),
        ]

    def save(self, *args, **kwargs):
        # Calculate total cost
        self.total_cost = abs(self.quantity) * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_type.title()} - {self.product.name} ({self.quantity} units)"


@tenant_aware_unique_together('adjustment_id')
class StockAdjustment(TenantAwareHistoricalModel):
    """Tenant-aware stock adjustment tracking"""
    
    _tenant_field = 'store__tenant'
    
    ADJUSTMENT_REASONS = [
        ('count_discrepancy', 'Physical Count Discrepancy'),
        ('damage', 'Damaged Goods'),
        ('theft', 'Theft/Loss'),
        ('expired', 'Expired Products'),
        ('system_error', 'System Error Correction'),
        ('other', 'Other'),
    ]
    
    adjustment_id = models.CharField(
        max_length=50,
        default=uuid.uuid4,
        verbose_name='Adjustment ID'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_adjustments',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_adjustments',
        verbose_name='Product Variant'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stock_adjustments',
        verbose_name='Store Location',
        help_text='Store location where this adjustment occurred'
    )
    reason = models.CharField(
        max_length=30,
        choices=ADJUSTMENT_REASONS,
        verbose_name='Adjustment Reason'
    )
    quantity_before = models.IntegerField(
        verbose_name='Quantity Before',
        help_text='Stock quantity before adjustment'
    )
    quantity_after = models.IntegerField(
        verbose_name='Quantity After',
        help_text='Stock quantity after adjustment'
    )
    adjustment_quantity = models.IntegerField(
        verbose_name='Adjustment Quantity',
        help_text='Difference in quantity (positive or negative)'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost',
        help_text='Cost per unit for valuation'
    )
    total_value_impact = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total Value Impact',
        help_text='Total financial impact of adjustment'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Detailed explanation of the adjustment'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Adjusted By'
    )
    adjustment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Adjustment Date'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        ordering = ['-adjustment_date']
        indexes = [
            models.Index(fields=['store', 'adjustment_date'], name='store_adjustment_date_idx'),
            models.Index(fields=['store', 'product'], name='store_product_adj_idx'),
            models.Index(fields=['store__tenant', 'adjustment_date'], name='tenant_adjustment_date_idx'),
        ]

    def save(self, *args, **kwargs):
        # Calculate adjustment quantity and value impact
        self.adjustment_quantity = self.quantity_after - self.quantity_before
        self.total_value_impact = self.adjustment_quantity * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Adjustment {self.adjustment_id} - {self.product.name}"



class ProductExpiration(TenantAwareHistoricalModel):
    """Tenant-aware product expiration tracking"""
    
    _tenant_field = 'store__tenant'
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='expiration_records',
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expiration_records',
        verbose_name='Product Variant'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='product_expirations',
        verbose_name='Store Location',
        help_text='Store location where this batch is located'
    )
    batch_number = models.CharField(
        max_length=100,
        verbose_name='Batch/Lot Number',
        help_text='Batch or lot number for tracking'
    )
    quantity = models.IntegerField(
        verbose_name='Quantity',
        help_text='Quantity in this batch'
    )
    manufacture_date = models.DateField(
        verbose_name='Manufacture Date'
    )
    expiration_date = models.DateField(
        verbose_name='Expiration Date'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost',
        help_text='Cost per unit for this batch'
    )
    is_expired = models.BooleanField(
        default=False,
        verbose_name='Is Expired',
        help_text='Indicates if this batch has expired'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Expiration'
        verbose_name_plural = 'Product Expirations'
        ordering = ['expiration_date']
        indexes = [
            models.Index(fields=['expiration_date', 'is_expired'], name='expiration_status_idx'),
            models.Index(fields=['product', 'expiration_date'], name='product_expiration_idx'),
            models.Index(fields=['store', 'expiration_date'], name='store_expiration_idx'),
            models.Index(fields=['store', 'is_expired'], name='store_expired_idx'),
            models.Index(fields=['store__tenant', 'expiration_date'], name='tenant_expiration_idx'),
        ]

    def days_until_expiration(self):
        """Calculate days until expiration"""
        if self.expiration_date:
            delta = self.expiration_date - timezone.now().date()
            return delta.days
        return None

    def is_near_expiration(self, days_threshold=7):
        """Check if product is near expiration"""
        days_left = self.days_until_expiration()
        return days_left is not None and 0 <= days_left <= days_threshold

    def __str__(self):
        return f"{self.product.name} - Batch {self.batch_number} (Exp: {self.expiration_date})"