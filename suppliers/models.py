
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords

# Python Imports
from decimal import Decimal



class Supplier(models.Model):
    """Represents a supplier from whom the store sources products."""

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Supplier Name',
        help_text='The official name of the supplier company or individual.'
    )
    contact_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Contact Person Name',
        help_text='Name of the primary contact person at the supplier.'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Contact Phone',
        help_text='Phone number for contacting the supplier.'
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name='Contact Email',
        help_text='Email address for contacting the supplier.'
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address',
        help_text='Physical address of the supplier.'
    )
    website = models.URLField(
        max_length=255,
        blank=True,
        verbose_name='Website',
        help_text='Supplier\'s website URL.'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description/Notes',
        help_text='Internal notes or description about the supplier.'
    )
    payment_terms = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Payment Terms',
        help_text='Payment terms offered by the supplier (e.g., Net 30, Net 60).'
    )
    currency = models.CharField(
        max_length=3,  # e.g., USD, EUR, GBP
        blank=True,
        verbose_name='Currency',
        help_text='Currency in which transactions are typically conducted with this supplier.'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Indicates if the supplier is currently active and being used.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']

    def __str__(self):
        return self.name
    


class SupplierProduct(models.Model):
    """Represents a product offered by a specific supplier, linking to the main Product catalog."""

    supplier = models.ForeignKey(
        'suppliers.Supplier',  # Use 'suppliers.Supplier' to avoid circular import issues
        on_delete=models.CASCADE,
        related_name='supplier_products',
        verbose_name='Supplier',
        help_text='The supplier offering this product.'
    )
    product = models.ForeignKey(
        'products.Product', # Use 'products.Product' to reference Product model from products app
        on_delete=models.CASCADE,
        related_name='supplier_products',
        verbose_name='Product',
        help_text='The main product catalog entry this supplier product corresponds to.'
    )
    supplier_sku = models.CharField(
        max_length=255,
        verbose_name='Supplier SKU/Product Code',
        help_text='The product code or SKU as used by the supplier.'
    )
    supplier_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Supplier Price',
        help_text='Current price offered by the supplier for this product.'
    )
    lead_time_days = models.IntegerField(
        default=0,
        verbose_name='Lead Time (Days)',
        help_text='Estimated lead time in days for the supplier to deliver this product.'
    )
    minimum_order_quantity = models.IntegerField(
        default=1,
        verbose_name='Minimum Order Quantity',
        help_text='Minimum quantity required when ordering this product from the supplier.'
    )
    currency = models.CharField(
        max_length=3,  # e.g., USD, EUR, GBP
        blank=True,
        verbose_name='Currency',
        help_text='Currency for the supplier price (if different from default supplier currency).'
    )
    last_price_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Price Updated'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Supplier Product'
        verbose_name_plural = 'Supplier Products'
        unique_together = ('supplier', 'product') # Ensure each product is listed only once per supplier

    def __str__(self):
        return f"{self.product.name} from {self.supplier.name} (SKU: {self.supplier_sku})"
    


class PurchaseOrder(models.Model):
    """Represents a purchase order placed with a supplier."""

    PO_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed by Supplier'),
        ('partially_shipped', 'Partially Shipped'),
        ('shipped', 'Shipped'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='PO Number',
        help_text='Unique Purchase Order number (auto-generated).',
        editable=False,  # Make it non-editable in admin form
        db_index=True
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        verbose_name='Supplier',
        help_text='Supplier for this purchase order.'
    )
    po_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='PO Date',
        help_text='Date the purchase order was created.',
        editable=False  # Non-editable in admin
    )
    expected_delivery_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Expected Delivery Date',
        help_text='Expected date of delivery from the supplier.'
    )
    shipping_address = models.TextField(
        blank=True,
        verbose_name='Shipping Address',
        help_text='Address to which the order should be shipped.'
    )
    billing_address = models.TextField(
        blank=True,
        verbose_name='Billing Address',
        help_text='Billing address for the purchase order.'
    )
    payment_terms = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Payment Terms',
        help_text='Payment terms for this specific purchase order (may override supplier defaults).'
    )
    currency = models.CharField(
        max_length=3,  # e.g., USD, EUR, GBP
        blank=True,
        verbose_name='Currency',
        help_text='Currency for this purchase order (may override supplier default).'
    )
    total_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Total Amount', 
        help_text='Total amount of the purchase Order (calculated)'
    )
    status = models.CharField(
        max_length=50,
        choices=PO_STATUS_CHOICES,
        default='draft',
        verbose_name='Status',
        help_text='Current status of the purchase order.'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Additional notes or comments about this purchase order.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-po_date']  # Order by PO date in reverse (most recent first)

    def __str__(self):
        return f"PO #{self.po_number} - {self.supplier.name} - Status: {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            # Auto-generate PO number if it's not already set on creation
            # You can customize the PO number format as needed
            prefix = 'PO'
            last_po = PurchaseOrder.objects.order_by('-id').first()
            if last_po:
                last_po_number = last_po.po_number
                if last_po_number.startswith(prefix) and last_po_number[len(prefix):].isdigit():
                    next_po_number_int = int(last_po_number[len(prefix):]) + 1
                    self.po_number = f"{prefix}{next_po_number_int:04d}" # e.g., PO0001, PO0002
                else:
                    self.po_number = f"{prefix}0001" # If last PO number doesn't match pattern
            else:
                self.po_number = f"{prefix}0001" # First PO
        super().save(*args, **kwargs)



class PurchaseOrderItem(models.Model):
    """Represents an item within a purchase order."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        null=True,
        related_name='po_items',
        verbose_name='Purchase Order',
        help_text='The purchase order this item belongs to.'
    )
    product = models.ForeignKey(
        'products.Product', # Reference Product model from products app
        on_delete=models.CASCADE,
        verbose_name='Product',
        help_text='The product being ordered.'
    )
    supplier_product = models.ForeignKey(
        'suppliers.SupplierProduct',
        on_delete=models.SET_NULL, # If SupplierProduct is deleted, keep PO Item but set supplier_product to NULL
        null=True,
        blank=True,
        verbose_name='Supplier Product (Optional)',
        help_text='Optional link to the Supplier Product catalog entry for this item.'
    )
    quantity_ordered = models.IntegerField(
        verbose_name='Quantity Ordered',
        help_text='Quantity of the product ordered.'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Price',
        help_text='Unit price for this item at the time of order.'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Discount Amount',
        help_text='Discount applied to this item (if any).'
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Tax Amount',
        help_text='Tax amount for this item (if applicable).'
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        verbose_name='Line Total',
        help_text='Calculated total for this line item (quantity * unit price - discount + tax).'
    )
    quantity_received = models.IntegerField(
        default=0,
        verbose_name='Quantity Received',
        help_text='Quantity of the product actually received from the supplier.'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Notes specific to this purchase order item.'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"Item for PO #{self.purchase_order.po_number} - {self.product.name} (Qty: {self.quantity_ordered})"

    def save(self, *args, **kwargs):
        # Calculate line total before saving
        self.line_total = (self.unit_price * self.quantity_ordered) - self.discount_amount + self.tax_amount
        super().save(*args, **kwargs)