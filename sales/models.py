# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F, Q
from customers.models import Customer
from products.models import Product, ProductVariant
from settings_app.models import Store

# Python Imports
from decimal import Decimal
import uuid
from datetime import datetime, timedelta


class PaymentMethod(models.Model):
    
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
    


class SaleTransaction(models.Model):
    
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
    history = HistoricalRecords()

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


class SaleItem(models.Model):
    
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
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
        indexes = [
            models.Index(fields=['store', 'product'], name='saleitem_store_product_idx'),
            models.Index(fields=['store', 'created_at'], name='saleitem_store_date_idx'),
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


class FinancialPeriod(models.Model):
    """Define financial reporting periods"""
    
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
        null=True,
        blank=True,
        related_name='financial_periods',
        verbose_name='Store Location',
        help_text='Store location for this period (null for company-wide periods)'
    )
    is_closed = models.BooleanField(
        default=False,
        verbose_name='Is Closed',
        help_text='Indicates if this period is closed for reporting'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Financial Period'
        verbose_name_plural = 'Financial Periods'
        ordering = ['-start_date']
        unique_together = ('period_type', 'start_date', 'end_date', 'store')

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


class SalesAnalytics(models.Model):
    """Detailed sales analytics and KPIs"""
    
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
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Sales Analytics'
        verbose_name_plural = 'Sales Analytics'
        ordering = ['-generated_at']
        unique_together = ('period', 'store')

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