# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from decimal import Decimal

# Python Imports


class Customer(models.Model):
    
    name = models.CharField(
        max_length=255,
        verbose_name='Customer Name'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,  # Optional: add index if you frequently query by phone
        verbose_name='Phone Number',
        help_text="Customer's phone number (optional)"
    )
    email = models.EmailField(
        blank=True,
        db_index=True,  # Optional: add index if you frequently query by email
        # unique=True,  # Uncomment if emails should be unique
        verbose_name='Email Address',
        help_text="Customer's email address (optional)"
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address',
        help_text="Customer's address (optional)"
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text="Any additional notes about the customer (optional)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['name']  # Default ordering by customer name

    def __str__(self):
        return self.name


class CustomerSegment(models.Model):
    """Customer segmentation for targeted marketing and pricing"""
    
    SEGMENT_TYPES = [
        ('demographic', 'Demographic'),
        ('behavioral', 'Behavioral'),
        ('geographic', 'Geographic'),
        ('psychographic', 'Psychographic'),
        ('value_based', 'Value-Based'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Segment Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    segment_type = models.CharField(
        max_length=20,
        choices=SEGMENT_TYPES,
        default='behavioral',
        verbose_name='Segment Type'
    )
    
    # Criteria for automatic segmentation
    min_total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Minimum Total Spent'
    )
    max_total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Maximum Total Spent'
    )
    min_purchase_frequency = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum Purchase Frequency (per year)'
    )
    min_avg_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Minimum Average Order Value'
    )
    days_since_last_purchase = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Days Since Last Purchase (max)'
    )
    
    # Segment benefits
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Default Discount %'
    )
    loyalty_points_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='Loyalty Points Multiplier'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer Segment'
        verbose_name_plural = 'Customer Segments'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    """Extended customer profile with analytics and segmentation"""
    
    CUSTOMER_TIERS = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('vip', 'VIP'),
    ]
    
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Customer'
    )
    segment = models.ForeignKey(
        CustomerSegment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name='Customer Segment'
    )
    
    # Customer Analytics
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Amount Spent'
    )
    total_orders = models.IntegerField(
        default=0,
        verbose_name='Total Number of Orders'
    )
    average_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Average Order Value'
    )
    last_purchase_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Purchase Date'
    )
    first_purchase_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='First Purchase Date'
    )
    
    # Customer Tier and Status
    tier = models.CharField(
        max_length=20,
        choices=CUSTOMER_TIERS,
        default='bronze',
        verbose_name='Customer Tier'
    )
    is_vip = models.BooleanField(
        default=False,
        verbose_name='VIP Status'
    )
    
    # Preferences
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('sms', 'SMS'),
            ('none', 'No Contact'),
        ],
        default='email',
        verbose_name='Preferred Contact Method'
    )
    marketing_opt_in = models.BooleanField(
        default=True,
        verbose_name='Marketing Opt-in'
    )
    
    # Calculated Fields
    customer_lifetime_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Customer Lifetime Value (CLV)'
    )
    purchase_frequency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Purchase Frequency (per year)'
    )
    days_since_last_purchase = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Days Since Last Purchase'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'
        ordering = ['-total_spent']

    def update_analytics(self):
        """Update customer analytics based on transaction history"""
        from sales.models import SaleTransaction
        
        transactions = SaleTransaction.objects.filter(
            customer=self.customer,
            status='completed'
        )
        
        if transactions.exists():
            self.total_orders = transactions.count()
            self.total_spent = transactions.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            
            if self.total_orders > 0:
                self.average_order_value = self.total_spent / self.total_orders
            
            self.first_purchase_date = transactions.order_by('sale_date').first().sale_date
            self.last_purchase_date = transactions.order_by('-sale_date').first().sale_date
            
            # Calculate days since last purchase
            if self.last_purchase_date:
                self.days_since_last_purchase = (
                    timezone.now().date() - self.last_purchase_date.date()
                ).days
            
            # Calculate purchase frequency (purchases per year)
            if self.first_purchase_date:
                days_active = (timezone.now() - self.first_purchase_date).days
                if days_active > 0:
                    self.purchase_frequency = (self.total_orders * 365) / days_active
            
            # Calculate CLV (simplified)
            self.customer_lifetime_value = self.average_order_value * self.purchase_frequency * 2  # 2 year projection
            
            # Update tier based on total spent
            if self.total_spent >= 10000:
                self.tier = 'vip'
                self.is_vip = True
            elif self.total_spent >= 5000:
                self.tier = 'platinum'
            elif self.total_spent >= 2000:
                self.tier = 'gold'
            elif self.total_spent >= 500:
                self.tier = 'silver'
            else:
                self.tier = 'bronze'
        
        self.save()

    def __str__(self):
        return f"{self.customer.name} Profile ({self.tier.title()})"


class LoyaltyProgram(models.Model):
    """Loyalty program configuration"""
    
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Program Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    
    # Points Configuration
    points_per_dollar = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='Points per Dollar Spent'
    )
    points_value = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0100'),
        verbose_name='Point Value (in currency)',
        help_text='How much each point is worth in currency'
    )
    
    # Redemption Rules
    min_points_redemption = models.IntegerField(
        default=100,
        verbose_name='Minimum Points for Redemption'
    )
    max_points_per_transaction = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Maximum Points per Transaction'
    )
    
    # Program Settings
    points_expiry_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Points Expiry (Days)',
        help_text='Days after which points expire (null = never expire)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )
    
    # Bonus Multipliers
    birthday_bonus_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('2.00'),
        verbose_name='Birthday Bonus Multiplier'
    )
    referral_bonus_points = models.IntegerField(
        default=500,
        verbose_name='Referral Bonus Points'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Loyalty Program'
        verbose_name_plural = 'Loyalty Programs'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerLoyaltyAccount(models.Model):
    """Individual customer loyalty account"""
    
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='loyalty_account',
        verbose_name='Customer'
    )
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='customer_accounts',
        verbose_name='Loyalty Program'
    )
    
    # Points Balance
    current_points = models.IntegerField(
        default=0,
        verbose_name='Current Points Balance'
    )
    lifetime_points_earned = models.IntegerField(
        default=0,
        verbose_name='Lifetime Points Earned'
    )
    lifetime_points_redeemed = models.IntegerField(
        default=0,
        verbose_name='Lifetime Points Redeemed'
    )
    
    # Account Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Account Active'
    )
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Enrollment Date'
    )
    last_activity_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Activity Date'
    )
    
    # Special Dates
    birthday = models.DateField(
        null=True,
        blank=True,
        verbose_name='Birthday'
    )
    anniversary_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Anniversary Date'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer Loyalty Account'
        verbose_name_plural = 'Customer Loyalty Accounts'
        unique_together = ('customer', 'program')
        ordering = ['-current_points']

    def add_points(self, points, transaction_type='purchase', reference_id=None, description=None):
        """Add points to customer account"""
        self.current_points += points
        self.lifetime_points_earned += points
        self.last_activity_date = timezone.now()
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            loyalty_account=self,
            transaction_type=transaction_type,
            points_change=points,
            points_balance_after=self.current_points,
            reference_id=reference_id,
            description=description or f"Earned {points} points"
        )

    def redeem_points(self, points, reference_id=None, description=None):
        """Redeem points from customer account"""
        if points > self.current_points:
            raise ValueError("Insufficient points balance")
        
        self.current_points -= points
        self.lifetime_points_redeemed += points
        self.last_activity_date = timezone.now()
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            loyalty_account=self,
            transaction_type='redemption',
            points_change=-points,
            points_balance_after=self.current_points,
            reference_id=reference_id,
            description=description or f"Redeemed {points} points"
        )

    def __str__(self):
        return f"{self.customer.name} - {self.current_points} points"


class LoyaltyTransaction(models.Model):
    """Track all loyalty point transactions"""
    
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase Earned'),
        ('bonus', 'Bonus Points'),
        ('redemption', 'Points Redemption'),
        ('adjustment', 'Manual Adjustment'),
        ('expiry', 'Points Expired'),
        ('refund', 'Refund Points'),
        ('birthday', 'Birthday Bonus'),
        ('referral', 'Referral Bonus'),
    ]
    
    loyalty_account = models.ForeignKey(
        CustomerLoyaltyAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Loyalty Account'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='Transaction Type'
    )
    points_change = models.IntegerField(
        verbose_name='Points Change',
        help_text='Positive for earned, negative for redeemed'
    )
    points_balance_after = models.IntegerField(
        verbose_name='Points Balance After Transaction'
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference ID',
        help_text='Reference to related sale, redemption, etc.'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    transaction_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Transaction Date'
    )
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Points Expiry Date'
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Loyalty Transaction'
        verbose_name_plural = 'Loyalty Transactions'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['loyalty_account', 'transaction_date'], name='loyalty_account_date_idx'),
            models.Index(fields=['transaction_type', 'transaction_date'], name='loyalty_type_date_idx'),
        ]

    def __str__(self):
        return f"{self.loyalty_account.customer.name} - {self.points_change} points ({self.transaction_type})"


class PromotionalCampaign(models.Model):
    """Marketing campaigns and promotions"""
    
    CAMPAIGN_TYPES = [
        ('discount', 'Discount Campaign'),
        ('bogo', 'Buy One Get One'),
        ('loyalty_bonus', 'Loyalty Bonus Points'),
        ('seasonal', 'Seasonal Promotion'),
        ('clearance', 'Clearance Sale'),
        ('new_customer', 'New Customer Offer'),
        ('referral', 'Referral Program'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(
        max_length=255,
        verbose_name='Campaign Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    campaign_type = models.CharField(
        max_length=20,
        choices=CAMPAIGN_TYPES,
        verbose_name='Campaign Type'
    )
    
    # Timing
    start_date = models.DateTimeField(
        verbose_name='Start Date'
    )
    end_date = models.DateTimeField(
        verbose_name='End Date'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )
    
    # Targeting
    target_segments = models.ManyToManyField(
        CustomerSegment,
        blank=True,
        related_name='campaigns',
        verbose_name='Target Customer Segments'
    )
    target_all_customers = models.BooleanField(
        default=False,
        verbose_name='Target All Customers'
    )
    
    # Discount Configuration
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Percentage Discount'),
            ('fixed_amount', 'Fixed Amount Discount'),
            ('bogo', 'Buy One Get One'),
            ('loyalty_points', 'Bonus Loyalty Points'),
        ],
        default='percentage',
        verbose_name='Discount Type'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Discount Value'
    )
    
    # Usage Limits
    max_uses_per_customer = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Max Uses per Customer'
    )
    total_usage_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Total Usage Limit'
    )
    current_usage_count = models.IntegerField(
        default=0,
        verbose_name='Current Usage Count'
    )
    
    # Conditions
    minimum_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Minimum Purchase Amount'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Promotional Campaign'
        verbose_name_plural = 'Promotional Campaigns'
        ordering = ['-start_date']

    def is_active(self):
        """Check if campaign is currently active"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.start_date <= now <= self.end_date and
            (self.total_usage_limit is None or self.current_usage_count < self.total_usage_limit)
        )

    def __str__(self):
        return f"{self.name} ({self.start_date.date()} - {self.end_date.date()})"