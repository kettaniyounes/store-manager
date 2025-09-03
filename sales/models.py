# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Q

# Python Imports
from decimal import Decimal
import uuid

# Local Imports
from settings_app.models import Store
from settings_app.base_models import TenantAwareHistoricalModel, SharedReferenceModel
from customers.models import Customer, CustomerSegment
from products.models import Product, ProductVariant, Category


class PaymentMethod(SharedReferenceModel):
    
    name = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name='Payment Method Name'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Description', 
        help_text='Optional description of the payment method'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Is Active', 
        help_text='Indicates if this payment method is currently active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['name']

    def __str__(self):
        return self.name
    

class SaleTransaction(TenantAwareHistoricalModel):
    """Tenant-aware sale transaction model"""
    
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        verbose_name='Transaction ID', 
        help_text='Unique transaction identifier (e.g., receipt number)'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='sale_transactions',
        verbose_name='Store Location',
        help_text='Store location where this sale was processed'
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sale_transactions', 
        verbose_name='Customer', 
        help_text='Optional customer associated with this sale'
    )
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sale_transactions', 
        verbose_name='Salesperson', 
        help_text='Optional salesperson who processed this sale'
    )
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT, 
        related_name='sale_transactions', 
        verbose_name='Payment Method', 
        help_text='Payment method used for this transaction'
    )
    sale_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Sale Date & Time', 
        help_text='Date and time of the sale transaction'
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Total Amount', 
        help_text='Total amount of the sale transaction (calculated)'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Discount Amount', 
        help_text='Total discount applied to the transaction'
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Tax Amount', 
        help_text='Total tax amount for the transaction'
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Cost',
        help_text='Total cost of goods sold for this transaction'
    )
    gross_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Gross Profit',
        help_text='Gross profit for this transaction (revenue - COGS)'
    )
    profit_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Profit Margin %',
        help_text='Profit margin percentage for this transaction'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('completed', 'Completed'),
            ('voided', 'Voided'),
        ],
        default='completed',
        verbose_name='Status',
        help_text='Indicates whether the sale is completed or voided'
    )
    notes = models.TextField(
        blank=True, 
        verbose_name='Notes', 
        help_text='Optional notes or comments for this transaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale Transaction'
        verbose_name_plural = 'Sale Transactions'
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['sale_date', 'status'], name='sale_date_status_idx'),
            models.Index(fields=['salesperson', 'sale_date'], name='salesperson_date_idx'),
            models.Index(fields=['customer', 'sale_date'], name='customer_date_idx'),
            models.Index(fields=['store', 'sale_date'], name='store_sale_date_idx'),
            models.Index(fields=['store', 'status'], name='store_status_idx'),
            models.Index(fields=['sale_date'], name='sale_date_idx'),
            models.Index(fields=['status'], name='sale_status_idx'),
            models.Index(fields=['transaction_id'], name='transaction_idx'),
        ]
        unique_together = [
            ('transaction_id',),
        ]

    def calculate_financial_metrics(self):
        """Calculate and update financial metrics for this transaction"""
        self.total_cost = sum(item.total_cost for item in self.sale_items.all())
        self.gross_profit = self.total_amount - self.total_cost
        
        if self.total_cost > 0:
            self.profit_margin_percentage = (self.gross_profit / self.total_amount) * 100
        else:
            self.profit_margin_percentage = Decimal('0.00')
        
        self.save(update_fields=['total_cost', 'gross_profit', 'profit_margin_percentage'])

    def __str__(self):
        return self.transaction_id


class SaleItem(TenantAwareHistoricalModel):
    """Tenant-aware sale item model"""
        
    sale_transaction = models.ForeignKey(
        SaleTransaction, 
        on_delete=models.CASCADE,
        related_name='sale_items', 
        verbose_name='Sale Transaction'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        related_name='sale_items', 
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='sale_items', 
        verbose_name='Product Variant', 
        help_text='Optional product variant if applicable'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name='Store Location',
        help_text='Store location where this item was sold from (for inventory tracking)'
    )
    quantity = models.IntegerField(
        verbose_name='Quantity', 
        help_text='Quantity of the product sold'
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Unit Price', 
        help_text='Price per unit at the time of sale'
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Cost',
        help_text='Cost per unit at the time of sale (for COGS calculation)'
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Total Cost',
        help_text='Total cost for this line item (quantity × unit cost)'
    )
    gross_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Gross Profit',
        help_text='Gross profit for this line item (line total - total cost)'
    )
    profit_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Profit Margin %',
        help_text='Profit margin percentage for this line item'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Discount Amount', 
        help_text='Discount applied to this sale item'
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name='Tax Amount', 
        help_text='Tax amount for this sale item'
    )
    line_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Line Total', 
        help_text='Total price for this sale item (calculated)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
        indexes = [
            models.Index(fields=['store', 'product'], name='saleitem_store_product_idx'),
            models.Index(fields=['store', 'created_at'], name='saleitem_store_date_idx'),
            models.Index(fields=['product'], name='saleitem_product_idx'),
            models.Index(fields=['created_at'], name='saleitem_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.store_id and self.sale_transaction_id:
            self.store = self.sale_transaction.store
        
        # Calculate financial metrics before saving
        self.total_cost = self.quantity * self.unit_cost
        self.gross_profit = self.line_total - self.total_cost
        
        if self.line_total > 0:
            self.profit_margin_percentage = (self.gross_profit / self.line_total) * 100
        else:
            self.profit_margin_percentage = Decimal('0.00')
        
        super().save(*args, **kwargs)

    def __str__(self):
        variant_info = f" - Variant: {self.product_variant}" if self.product_variant else ""
        return f"Item for Sale: {self.sale_transaction.transaction_id} - Product: {self.product.name}{variant_info}"


class FinancialPeriod(TenantAwareHistoricalModel):
    """Tenant-aware financial reporting periods"""
        
    PERIOD_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Period'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Period Name',
        help_text='Name of the financial period (e.g., "Q1 2024", "January 2024")'
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPES,
        verbose_name='Period Type'
    )
    start_date = models.DateField(
        verbose_name='Start Date'
    )
    end_date = models.DateField(
        verbose_name='End Date'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='financial_periods',
        verbose_name='Store Location',
        help_text='Store location for this period (null for company-wide periods)'
    )
    is_closed = models.BooleanField(
        default=False,
        verbose_name='Is Closed',
        help_text='Whether this period is closed for reporting'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Financial Period'
        verbose_name_plural = 'Financial Periods'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['start_date'], name='period_start_idx'),
            models.Index(fields=['period_type'], name='period_type_idx'),
        ]

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"{self.name} ({self.start_date} to {self.end_date}){store_info}"


class ProfitLossReport(models.Model):
    """Profit and Loss statement data"""
    
    period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.CASCADE,
        related_name='profit_loss_reports',
        verbose_name='Financial Period'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='profit_loss_reports',
        verbose_name='Store Location',
        help_text='Store location for this report (null for company-wide reports)'
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Revenue'
    )
    total_cogs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Cost of Goods Sold'
    )
    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Gross Profit'
    )
    total_discounts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Discounts Given'
    )
    total_taxes_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Taxes Collected'
    )
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Net Profit'
    )
    profit_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Profit Margin %'
    )
    transaction_count = models.IntegerField(
        default=0,
        verbose_name='Number of Transactions'
    )
    average_transaction_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Transaction Value'
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Generated At'
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Profit & Loss Report'
        verbose_name_plural = 'Profit & Loss Reports'
        ordering = ['-generated_at']
        unique_together = ('period', 'store')

    def calculate_metrics(self):
        """Calculate all financial metrics for this period"""
        transactions = SaleTransaction.objects.filter(
            sale_date__range=[self.period.start_date, self.period.end_date],
            status='completed'
        )
        
        if self.store:
            transactions = transactions.filter(store=self.store)
        
        self.total_revenue = transactions.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        self.total_cogs = transactions.aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')
        
        self.gross_profit = self.total_revenue - self.total_cogs
        
        self.total_discounts = transactions.aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0.00')
        
        self.total_taxes_collected = transactions.aggregate(
            total=Sum('tax_amount')
        )['total'] or Decimal('0.00')
        
        self.net_profit = self.gross_profit
        
        if self.total_revenue > 0:
            self.profit_margin_percentage = (self.net_profit / self.total_revenue) * 100
        
        self.transaction_count = transactions.count()
        
        if self.transaction_count > 0:
            self.average_transaction_value = self.total_revenue / self.transaction_count
        
        self.save()

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"P&L Report for {self.period.name}{store_info}"


class SalesAnalytics(TenantAwareHistoricalModel):
    """Tenant-aware sales analytics and KPIs"""
        
    period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.CASCADE,
        related_name='sales_analytics',
        verbose_name='Financial Period'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales_analytics',
        verbose_name='Store Location',
        help_text='Store location for this analytics report (null for company-wide)'
    )
    # Revenue metrics
    total_sales_volume = models.IntegerField(
        default=0,
        verbose_name='Total Items Sold'
    )
    average_items_per_transaction = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Items per Transaction'
    )
    # Customer metrics
    unique_customers = models.IntegerField(
        default=0,
        verbose_name='Unique Customers'
    )
    new_customers = models.IntegerField(
        default=0,
        verbose_name='New Customers'
    )
    repeat_customers = models.IntegerField(
        default=0,
        verbose_name='Repeat Customers'
    )
    # Payment method breakdown
    cash_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Cash Sales'
    )
    card_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Card Sales'
    )
    other_payment_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Other Payment Methods'
    )
    # Top performing metrics
    top_selling_product_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Top Selling Product ID'
    )
    top_selling_category_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Top Selling Category ID'
    )
    best_salesperson_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Best Salesperson ID'
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Generated At'
    )

    class Meta:
        verbose_name = 'Sales Analytics'
        verbose_name_plural = 'Sales Analytics'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['generated_at'], name='analytics_date_idx'),
        ]

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"Sales Analytics for {self.period.name}{store_info}"


class TaxReport(models.Model):
    """Tax reporting and compliance"""
    
    period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.CASCADE,
        related_name='tax_reports',
        verbose_name='Financial Period'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tax_reports',
        verbose_name='Store Location',
        help_text='Store location for this tax report (null for company-wide)'
    )
    total_taxable_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Taxable Sales'
    )
    total_tax_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Tax Collected'
    )
    tax_exempt_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Tax Exempt Sales'
    )
    average_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Tax Rate %'
    )
    tax_by_rate = models.JSONField(
        default=dict,
        verbose_name='Tax Breakdown by Rate',
        help_text='JSON object containing tax amounts by rate'
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Generated At'
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Tax Report'
        verbose_name_plural = 'Tax Reports'
        ordering = ['-generated_at']
        unique_together = ('period', 'store')

    def __str__(self):
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"Tax Report for {self.period.name}{store_info}"


class PricingRule(models.Model):
    """Advanced pricing rules for dynamic pricing"""
    
    RULE_TYPES = [
        ('bulk_discount', 'Bulk Discount'),
        ('time_based', 'Time-Based Pricing'),
        ('customer_tier', 'Customer Tier Pricing'),
        ('seasonal', 'Seasonal Pricing'),
        ('clearance', 'Clearance Pricing'),
        ('promotional', 'Promotional Pricing'),
        ('dynamic', 'Dynamic Pricing'),
    ]
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage Discount'),
        ('fixed_amount', 'Fixed Amount Discount'),
        ('fixed_price', 'Fixed Price Override'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Rule Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPES,
        verbose_name='Rule Type'
    )
    
    # Product Targeting
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='pricing_rules',
        verbose_name='Target Products'
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name='pricing_rules',
        verbose_name='Target Categories'
    )
    apply_to_all_products = models.BooleanField(
        default=False,
        verbose_name='Apply to All Products'
    )
    
    # Customer Targeting
    customer_segments = models.ManyToManyField(
        CustomerSegment,
        blank=True,
        related_name='pricing_rules',
        verbose_name='Target Customer Segments'
    )
    customer_tiers = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Target Customer Tiers',
        help_text='List of customer tiers this rule applies to'
    )
    
    # Pricing Configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
        verbose_name='Discount Type'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Discount Value'
    )
    
    # Quantity-based rules
    min_quantity = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum Quantity'
    )
    max_quantity = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Maximum Quantity'
    )
    
    # Time-based rules
    start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Start Time'
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='End Time'
    )
    days_of_week = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Days of Week',
        help_text='List of days (0=Monday, 6=Sunday) when rule applies'
    )
    
    # Date range
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Start Date'
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='End Date'
    )
    
    # Rule priority and status
    priority = models.IntegerField(
        default=0,
        verbose_name='Priority',
        help_text='Higher numbers have higher priority'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Pricing Rule'
        verbose_name_plural = 'Pricing Rules'
        ordering = ['-priority', 'name']

    def calculate_price(self, original_price, quantity=1):
        """Calculate the adjusted price based on this rule"""
        if self.discount_type == 'percentage':
            return original_price * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed_amount':
            return max(Decimal('0.00'), original_price - self.discount_value)
        elif self.discount_type == 'fixed_price':
            return self.discount_value
        return original_price

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class SalesReturn(TenantAwareHistoricalModel):
    """Tenant-aware sales return model"""
        
    RETURN_REASONS = [
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_satisfied', 'Customer Not Satisfied'),
        ('damaged_shipping', 'Damaged During Shipping'),
        ('expired', 'Expired Product'),
        ('duplicate', 'Duplicate Purchase'),
        ('other', 'Other Reason'),
    ]
    
    RETURN_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
        ('refunded', 'Refunded'),
    ]
    
    REFUND_METHODS = [
        ('original_payment', 'Original Payment Method'),
        ('store_credit', 'Store Credit'),
        ('cash', 'Cash Refund'),
        ('exchange', 'Product Exchange'),
    ]
    
    return_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Return Number'
    )
    original_sale = models.ForeignKey(
        SaleTransaction,
        on_delete=models.CASCADE,
        related_name='returns',
        verbose_name='Original Sale Transaction'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='returns',
        verbose_name='Customer'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='returns',
        verbose_name='Store Location'
    )
    
    # Return Details
    return_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Return Date'
    )
    reason = models.CharField(
        max_length=20,
        choices=RETURN_REASONS,
        verbose_name='Return Reason'
    )
    status = models.CharField(
        max_length=20,
        choices=RETURN_STATUS,
        default='pending',
        verbose_name='Return Status'
    )
    
    # Financial Information
    total_return_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Return Amount'
    )
    refund_method = models.CharField(
        max_length=20,
        choices=REFUND_METHODS,
        default='original_payment',
        verbose_name='Refund Method'
    )
    
    # Processing Information
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns',
        verbose_name='Processed By'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sales Return'
        verbose_name_plural = 'Sales Returns'
        ordering = ['-return_date']
        indexes = [
            models.Index(fields=['return_date'], name='return_date_idx'),
            models.Index(fields=['status'], name='return_status_idx'),
        ]
        unique_together = [
            ('return_number',),
        ]

    def __str__(self):
        return f"Return {self.return_number} - {self.customer.name}"


class SalesReturnItem(TenantAwareHistoricalModel):
    """Tenant-aware sales return item model"""
        
    sales_return = models.ForeignKey(
        SalesReturn,
        on_delete=models.CASCADE,
        related_name='return_items',
        verbose_name='Sales Return'
    )
    original_sale_item = models.ForeignKey(
        SaleItem,
        on_delete=models.CASCADE,
        related_name='return_items',
        verbose_name='Original Sale Item'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Product'
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Product Variant'
    )
    
    # Return Quantities and Pricing
    quantity_returned = models.IntegerField(
        verbose_name='Quantity Returned'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Unit Price'
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Line Total'
    )
    
    # Item Condition
    condition = models.CharField(
        max_length=20,
        choices=[
            ('new', 'Like New'),
            ('good', 'Good Condition'),
            ('fair', 'Fair Condition'),
            ('poor', 'Poor Condition'),
            ('damaged', 'Damaged'),
        ],
        default='good',
        verbose_name='Item Condition'
    )
    can_resell = models.BooleanField(
        default=True,
        verbose_name='Can Resell'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Item Notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sales Return Item'
        verbose_name_plural = 'Sales Return Items'

    def save(self, *args, **kwargs):
        self.line_total = self.quantity_returned * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Return Item: {self.product.name} (Qty: {self.quantity_returned})"


class SalesForecast(TenantAwareHistoricalModel):
    """Tenant-aware sales forecasting model"""
        
    FORECAST_METHODS = [
        ('moving_average', 'Moving Average'),
        ('exponential_smoothing', 'Exponential Smoothing'),
        ('linear_regression', 'Linear Regression'),
        ('seasonal_decomposition', 'Seasonal Decomposition'),
        ('arima', 'ARIMA Model'),
    ]
    
    FORECAST_PERIODS = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales_forecasts',
        verbose_name='Store Location',
        help_text='Store location for forecast (null for company-wide)'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales_forecasts',
        verbose_name='Product',
        help_text='Product for forecast (null for overall sales)'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales_forecasts',
        verbose_name='Category',
        help_text='Category for forecast (null for overall sales)'
    )
    
    # Forecast Configuration
    forecast_period = models.CharField(
        max_length=20,
        choices=FORECAST_PERIODS,
        default='monthly',
        verbose_name='Forecast Period'
    )
    forecast_method = models.CharField(
        max_length=30,
        choices=FORECAST_METHODS,
        default='moving_average',
        verbose_name='Forecasting Method'
    )
    
    # Time Range
    forecast_start_date = models.DateField(
        verbose_name='Forecast Start Date'
    )
    forecast_end_date = models.DateField(
        verbose_name='Forecast End Date'
    )
    historical_data_start = models.DateField(
        verbose_name='Historical Data Start Date'
    )
    
    # Forecast Results
    predicted_sales_quantity = models.IntegerField(
        default=0,
        verbose_name='Predicted Sales Quantity'
    )
    predicted_sales_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Predicted Sales Revenue'
    )
    confidence_interval_lower = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Confidence Interval (Lower)'
    )
    confidence_interval_upper = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Confidence Interval (Upper)'
    )
    forecast_data = models.JSONField(
        default=dict,
        verbose_name='Forecast Data',
        help_text='JSON containing forecast values and confidence intervals'
    )
    # Model Performance
    accuracy_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Forecast Accuracy (%)'
    )
    mean_absolute_error = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Mean Absolute Error'
    )
    
    # Seasonal and Trend Factors
    seasonal_factor = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('1.000'),
        verbose_name='Seasonal Factor'
    )
    trend_factor = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('1.000'),
        verbose_name='Trend Factor'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sales Forecast'
        verbose_name_plural = 'Sales Forecasts'
        ordering = ['-forecast_start_date']
        indexes = [
            models.Index(fields=['forecast_start_date'], name='forecast_date_idx'),
        ]

    def __str__(self):
        target = "Overall"
        if self.product:
            scope = f"Product: {self.product.name}"
        elif self.category:
            scope = f"Category: {self.category.name}"
        
        store_info = f" - {self.store.name}" if self.store else " - Company Wide"
        return f"Forecast: {scope}{store_info}"