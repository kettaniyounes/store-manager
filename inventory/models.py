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
    

class SupplierPerformance(models.Model):
    """Track supplier performance metrics and ratings"""
    
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.CASCADE,
        related_name='performance_records',
        verbose_name='Supplier'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='supplier_performance',
        verbose_name='Product'
    )
    evaluation_period_start = models.DateField(
        verbose_name='Evaluation Period Start'
    )
    evaluation_period_end = models.DateField(
        verbose_name='Evaluation Period End'
    )
    
    # Performance Metrics
    total_orders = models.IntegerField(
        default=0,
        verbose_name='Total Orders'
    )
    on_time_deliveries = models.IntegerField(
        default=0,
        verbose_name='On-Time Deliveries'
    )
    quality_rating = models.IntegerField(
        choices=RATING_CHOICES,
        default=3,
        verbose_name='Quality Rating'
    )
    price_competitiveness = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        verbose_name='Price Competitiveness (1-5)',
        help_text='Rating of price competitiveness compared to market'
    )
    communication_rating = models.IntegerField(
        choices=RATING_CHOICES,
        default=3,
        verbose_name='Communication Rating'
    )
    
    # Calculated Metrics
    on_time_delivery_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='On-Time Delivery Rate (%)'
    )
    average_lead_time_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        verbose_name='Average Lead Time (Days)'
    )
    defect_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Defect Rate (%)'
    )
    overall_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Overall Performance Score'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Performance Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Supplier Performance'
        verbose_name_plural = 'Supplier Performance Records'
        unique_together = ('supplier', 'product', 'evaluation_period_start')
        ordering = ['-evaluation_period_end']

    def save(self, *args, **kwargs):
        # Calculate on-time delivery rate
        if self.total_orders > 0:
            self.on_time_delivery_rate = (self.on_time_deliveries / self.total_orders) * 100
        
        # Calculate overall score (weighted average)
        weights = {
            'on_time_rate': 0.3,
            'quality': 0.25,
            'price': 0.2,
            'communication': 0.15,
            'defect_rate': 0.1
        }
        
        on_time_score = min(self.on_time_delivery_rate / 20, 5)  # Convert % to 1-5 scale
        defect_score = max(5 - (self.defect_rate / 2), 1)  # Lower defect rate = higher score
        
        self.overall_score = (
            weights['on_time_rate'] * on_time_score +
            weights['quality'] * self.quality_rating +
            weights['price'] * self.price_competitiveness +
            weights['communication'] * self.communication_rating +
            weights['defect_rate'] * defect_score
        )
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier.name} - {self.product.name} ({self.evaluation_period_start} to {self.evaluation_period_end})"


class BatchLotTracking(models.Model):
    """Enhanced batch/lot tracking for products with expiration dates"""
    
    BATCH_STATUS = [
        ('active', 'Active'),
        ('quarantined', 'Quarantined'),
        ('expired', 'Expired'),
        ('recalled', 'Recalled'),
        ('sold_out', 'Sold Out'),
    ]
    
    batch_number = models.CharField(
        max_length=100,
        verbose_name='Batch/Lot Number'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='batch_lots',
        verbose_name='Product'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='batch_lots',
        verbose_name='Store'
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batch_lots',
        verbose_name='Supplier'
    )
    
    # Batch Information
    manufacture_date = models.DateField(
        verbose_name='Manufacture Date'
    )
    expiration_date = models.DateField(
        verbose_name='Expiration Date'
    )
    received_date = models.DateField(
        default=timezone.now,
        verbose_name='Received Date'
    )
    
    # Quantity Tracking
    initial_quantity = models.IntegerField(
        verbose_name='Initial Quantity'
    )
    current_quantity = models.IntegerField(
        verbose_name='Current Quantity'
    )
    reserved_quantity = models.IntegerField(
        default=0,
        verbose_name='Reserved Quantity'
    )
    
    # Cost Information
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
    
    # Status and Quality
    status = models.CharField(
        max_length=20,
        choices=BATCH_STATUS,
        default='active',
        verbose_name='Batch Status'
    )
    quality_grade = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Quality Grade',
        help_text='A, B, C grade or custom grading'
    )
    
    # Traceability
    purchase_order_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Purchase Order Number'
    )
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Certificate Number'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Batch/Lot Tracking'
        verbose_name_plural = 'Batch/Lot Tracking Records'
        unique_together = ('batch_number', 'product', 'store')
        ordering = ['expiration_date']
        indexes = [
            models.Index(fields=['expiration_date', 'status'], name='batch_expiry_status_idx'),
            models.Index(fields=['product', 'store', 'status'], name='batch_product_store_idx'),
            models.Index(fields=['supplier', 'manufacture_date'], name='batch_supplier_mfg_idx'),
        ]

    def save(self, *args, **kwargs):
        self.total_cost = self.current_quantity * self.unit_cost
        
        # Auto-update status based on expiration
        if self.expiration_date < timezone.now().date() and self.status == 'active':
            self.status = 'expired'
        elif self.current_quantity <= 0 and self.status == 'active':
            self.status = 'sold_out'
        
        super().save(*args, **kwargs)

    def days_until_expiration(self):
        """Calculate days until expiration"""
        if self.expiration_date:
            delta = self.expiration_date - timezone.now().date()
            return delta.days
        return None

    def is_near_expiration(self, days_threshold=7):
        """Check if batch is near expiration"""
        days_left = self.days_until_expiration()
        return days_left is not None and 0 <= days_left <= days_threshold

    def available_quantity(self):
        """Get available quantity (current - reserved)"""
        return max(0, self.current_quantity - self.reserved_quantity)

    def __str__(self):
        return f"Batch {self.batch_number} - {self.product.name} (Exp: {self.expiration_date})"


class BarcodeScanning(models.Model):
    """Track barcode scanning activities and integrations"""
    
    SCAN_TYPES = [
        ('receiving', 'Receiving'),
        ('sale', 'Sale'),
        ('count', 'Physical Count'),
        ('transfer', 'Transfer'),
        ('lookup', 'Product Lookup'),
    ]
    
    barcode = models.CharField(
        max_length=100,
        verbose_name='Barcode',
        db_index=True
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='barcode_scans',
        verbose_name='Product'
    )
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='barcode_scans',
        verbose_name='Store'
    )
    scan_type = models.CharField(
        max_length=20,
        choices=SCAN_TYPES,
        verbose_name='Scan Type'
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name='Quantity'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Scanned By'
    )
    device_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Device ID',
        help_text='ID of scanning device or mobile app'
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference ID',
        help_text='Reference to related transaction'
    )
    scan_timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Scan Timestamp'
    )
    is_successful = models.BooleanField(
        default=True,
        verbose_name='Scan Successful'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Error Message'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Barcode Scanning'
        verbose_name_plural = 'Barcode Scanning Records'
        ordering = ['-scan_timestamp']
        indexes = [
            models.Index(fields=['barcode', 'scan_timestamp'], name='barcode_scan_time_idx'),
            models.Index(fields=['store', 'scan_type'], name='store_scan_type_idx'),
            models.Index(fields=['user', 'scan_timestamp'], name='user_scan_time_idx'),
        ]

    def __str__(self):
        product_name = self.product.name if self.product else 'Unknown Product'
        return f"Scan: {self.barcode} - {product_name} ({self.scan_type})"


class SmartReorderRule(models.Model):
    """Advanced reorder rules with multiple calculation methods"""
    
    CALCULATION_METHODS = [
        ('fixed', 'Fixed Reorder Point'),
        ('sales_velocity', 'Sales Velocity Based'),
        ('seasonal_adjusted', 'Seasonal Adjusted'),
        ('min_max', 'Min-Max Method'),
        ('economic_order_quantity', 'Economic Order Quantity'),
        ('predictive', 'Predictive Analytics'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    store = models.ForeignKey(
        'settings_app.Store',
        on_delete=models.CASCADE,
        related_name='reorder_rules',
        verbose_name='Store'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reorder_rules',
        verbose_name='Product'
    )
    
    # Rule Configuration
    calculation_method = models.CharField(
        max_length=30,
        choices=CALCULATION_METHODS,
        default='sales_velocity',
        verbose_name='Calculation Method'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium',
        verbose_name='Priority'
    )
    
    # Parameters
    lead_time_days = models.IntegerField(
        default=7,
        verbose_name='Lead Time (Days)'
    )
    safety_stock_days = models.IntegerField(
        default=3,
        verbose_name='Safety Stock (Days)'
    )
    review_period_days = models.IntegerField(
        default=30,
        verbose_name='Review Period (Days)'
    )
    service_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('95.00'),
        verbose_name='Service Level (%)'
    )
    
    # Calculated Values
    current_reorder_point = models.IntegerField(
        default=0,
        verbose_name='Current Reorder Point'
    )
    current_order_quantity = models.IntegerField(
        default=0,
        verbose_name='Current Order Quantity'
    )
    sales_velocity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Sales Velocity (units/day)'
    )
    demand_variability = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Demand Variability (std dev)'
    )
    
    # Last Calculation
    last_calculated = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Calculated'
    )
    calculation_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Calculation Accuracy (%)'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Smart Reorder Rule'
        verbose_name_plural = 'Smart Reorder Rules'
        unique_together = ('store', 'product')
        ordering = ['priority', 'product__name']
        indexes = [
            models.Index(fields=['store', 'is_active'], name='reorder_store_active_idx'),
            models.Index(fields=['priority', 'last_calculated'], name='reorder_priority_calc_idx'),
        ]

    def calculate_reorder_point(self):
        """Calculate optimal reorder point based on selected method"""
        if self.calculation_method == 'sales_velocity':
            # Reorder Point = (Average Daily Sales × Lead Time) + Safety Stock
            safety_stock = self.sales_velocity * self.safety_stock_days
            reorder_point = (self.sales_velocity * self.lead_time_days) + safety_stock
            return int(reorder_point)
        
        elif self.calculation_method == 'min_max':
            # Simple min-max calculation
            min_stock = self.sales_velocity * self.lead_time_days
            max_stock = min_stock * 2
            return int(min_stock)
        
        # Add more calculation methods as needed
        return self.current_reorder_point

    def __str__(self):
        return f"Reorder Rule: {self.store.name} - {self.product.name} ({self.calculation_method})"