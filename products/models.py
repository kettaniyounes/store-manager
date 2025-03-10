
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError

# Python Imports
from decimal import Decimal



class Category(models.Model):

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
    


class Brand(models.Model):

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
    


class Product(models.Model):

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
        unique=True,
        db_index=True,
        verbose_name='SKU',
        help_text='Stock Keeping Unit - unique product identifier'
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
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
    ) # Allow brand to be null, SET_NULL on delete, related_name, to_field='name' example
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
        verbose_name='Stock Quantity',
        help_text='Current stock quantity'
    )
    low_stock_threshold = models.IntegerField(
        default=10,
        verbose_name='Low Stock Threshold',
        help_text='Quantity below which low stock alerts are triggered'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Indicates if the product is active and available for sale'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category', 'selling_price'], name='category_price_idx'), # Example combined index
        ]
    
    def clean(self):
        # Validate that selling price is not less than cost price
        if self.selling_price < self.cost_price:
            raise ValidationError("Selling price cannot be less than cost price.")

    def __str__(self):
        return self.name
    

class ProductImage(models.Model):

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
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"Image for {self.product.name} (ID: {self.id})"
    

class ProductVariant(models.Model):
    
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
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        unique_together = ('product', 'name', 'value') # Ensure uniqueness for variant options within a product
        ordering = ['name', 'value']

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}" # More informative __str__