# Django Import
from rest_framework import serializers


# Python Import

# Local Imports
from .models import (
    Customer, CustomerProfile, CustomerSegment, LoyaltyProgram, 
    CustomerLoyaltyAccount, LoyaltyTransaction, PromotionalCampaign
)
from settings_app.base_serializers import (
    TenantAwareModelSerializer, SharedReferenceModelSerializer, 
    TenantFilteredPrimaryKeyRelatedField
)

class CustomerSerializer(TenantAwareModelSerializer):
    
    name = serializers.CharField(max_length=255, required=True) # Make 'name' explicitly required
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True) # 'phone_number' optional, allow blank
    email = serializers.EmailField(required=False, allow_blank=True) # 'email' optional, allow blank, EmailField for validation
    address = serializers.CharField(required=False, allow_blank=True) # 'address' optional, allow blank
    notes = serializers.CharField(required=False, allow_blank=True) # 'notes' optional, allow blank
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone_number', 'email', 'address', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSegmentSerializer(SharedReferenceModelSerializer):
    """Serializer for customer segments (shared across tenants)"""
    
    class Meta:
        model = CustomerSegment
        fields = [
            'id', 'name', 'description', 'segment_type', 'min_total_spent', 'max_total_spent',
            'min_purchase_frequency', 'min_avg_order_value', 'days_since_last_purchase',
            'discount_percentage', 'loyalty_points_multiplier', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerProfileSerializer(TenantAwareModelSerializer):
    """Serializer for customer profiles with analytics"""
    
    customer = TenantFilteredPrimaryKeyRelatedField(queryset=Customer.objects.all())
    segment = serializers.PrimaryKeyRelatedField(queryset=CustomerSegment.objects.all(), allow_null=True, required=False)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    segment_name = serializers.CharField(source='segment.name', read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'customer', 'customer_name', 'segment', 'segment_name', 'total_spent', 'total_orders',
            'average_order_value', 'last_purchase_date', 'first_purchase_date', 'tier', 'is_vip',
            'preferred_contact_method', 'marketing_opt_in', 'customer_lifetime_value',
            'purchase_frequency', 'days_since_last_purchase', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoyaltyProgramSerializer(SharedReferenceModelSerializer):
    """Serializer for loyalty programs (shared across tenants)"""
    
    class Meta:
        model = LoyaltyProgram
        fields = [
            'id', 'name', 'description', 'points_per_dollar', 'points_value', 'min_points_redemption',
            'max_points_per_transaction', 'points_expiry_days', 'is_active', 'birthday_bonus_multiplier',
            'referral_bonus_points', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerLoyaltyAccountSerializer(TenantAwareModelSerializer):
    """Serializer for customer loyalty accounts"""
    
    customer = TenantFilteredPrimaryKeyRelatedField(queryset=Customer.objects.all())
    program = serializers.PrimaryKeyRelatedField(queryset=LoyaltyProgram.objects.all())
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = CustomerLoyaltyAccount
        fields = [
            'id', 'customer', 'customer_name', 'program', 'program_name', 'current_points',
            'lifetime_points_earned', 'lifetime_points_redeemed', 'is_active', 'enrollment_date',
            'last_activity_date', 'birthday', 'anniversary_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']


class LoyaltyTransactionSerializer(TenantAwareModelSerializer):
    """Serializer for loyalty point transactions"""
    
    loyalty_account = TenantFilteredPrimaryKeyRelatedField(queryset=CustomerLoyaltyAccount.objects.all())
    customer_name = serializers.CharField(source='loyalty_account.customer.name', read_only=True)
    
    class Meta:
        model = LoyaltyTransaction
        fields = [
            'id', 'loyalty_account', 'customer_name', 'transaction_type', 'points_change',
            'points_balance_after', 'reference_id', 'description', 'transaction_date',
            'expiry_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'transaction_date', 'created_at', 'updated_at']


class PromotionalCampaignSerializer(TenantAwareModelSerializer):
    """Serializer for promotional campaigns"""
    
    target_segments = serializers.PrimaryKeyRelatedField(queryset=CustomerSegment.objects.all(), many=True, required=False)
    segment_names = serializers.StringRelatedField(source='target_segments', many=True, read_only=True)
    
    class Meta:
        model = PromotionalCampaign
        fields = [
            'id', 'name', 'description', 'campaign_type', 'start_date', 'end_date', 'status',
            'target_segments', 'segment_names', 'target_all_customers', 'discount_type', 'discount_value',
            'max_uses_per_customer', 'total_usage_limit', 'current_usage_count', 'minimum_purchase_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_usage_count', 'created_at', 'updated_at']