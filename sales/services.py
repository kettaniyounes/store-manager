from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import numpy as np
from typing import Dict, List, Optional
import structlog
from .models import (
    SaleTransaction, SaleItem, PricingRule, SalesForecast, SalesReturn
)
from customers.models import (
    Customer, CustomerProfile, CustomerSegment, CustomerLoyaltyAccount,
    PromotionalCampaign
)
from products.models import Product

logger = structlog.get_logger(__name__)


class PricingService:
    """Advanced pricing engine with dynamic rules"""
    
    @staticmethod
    def calculate_price(product: Product, customer: Optional[Customer] = None, 
                       quantity: int = 1, store_id: Optional[int] = None) -> Dict:
        """Calculate final price considering all applicable pricing rules"""
        
        base_price = product.selling_price
        original_price = base_price
        applied_rules = []
        final_price = base_price
        
        # Get customer profile if available
        customer_profile = None
        if customer:
            try:
                customer_profile = customer.profile
            except CustomerProfile.DoesNotExist:
                pass
        
        # Get applicable pricing rules
        applicable_rules = PricingRule.objects.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).order_by('-priority')
        
        # Filter rules by product
        product_rules = []
        for rule in applicable_rules:
            if rule.apply_to_all_products:
                product_rules.append(rule)
            elif rule.products.filter(id=product.id).exists():
                product_rules.append(rule)
            elif rule.categories.filter(id=product.category.id).exists():
                product_rules.append(rule)
        
        # Apply rules in priority order
        for rule in product_rules:
            if PricingService._rule_applies(rule, customer_profile, quantity):
                rule_price = rule.calculate_price(final_price, quantity)
                if rule_price != final_price:
                    applied_rules.append({
                        'rule_name': rule.name,
                        'rule_type': rule.rule_type,
                        'discount_value': rule.discount_value,
                        'price_before': final_price,
                        'price_after': rule_price
                    })
                    final_price = rule_price
        
        # Calculate total savings
        total_savings = original_price - final_price
        savings_percentage = (total_savings / original_price * 100) if original_price > 0 else 0
        
        return {
            'original_price': original_price,
            'final_price': final_price,
            'total_savings': total_savings,
            'savings_percentage': savings_percentage,
            'applied_rules': applied_rules,
            'quantity': quantity,
            'line_total': final_price * quantity
        }
    
    @staticmethod
    def _rule_applies(rule: PricingRule, customer_profile: Optional[CustomerProfile], 
                     quantity: int) -> bool:
        """Check if a pricing rule applies to the current context"""
        
        # Check quantity constraints
        if rule.min_quantity and quantity < rule.min_quantity:
            return False
        if rule.max_quantity and quantity > rule.max_quantity:
            return False
        
        # Check customer segment constraints
        if customer_profile and rule.customer_segments.exists():
            if not rule.customer_segments.filter(id=customer_profile.segment_id).exists():
                return False
        
        # Check customer tier constraints
        if customer_profile and rule.customer_tiers:
            if customer_profile.tier not in rule.customer_tiers:
                return False
        
        # Check time constraints
        now = timezone.now()
        if rule.start_time and rule.end_time:
            current_time = now.time()
            if not (rule.start_time <= current_time <= rule.end_time):
                return False
        
        # Check day of week constraints
        if rule.days_of_week:
            current_day = now.weekday()  # 0=Monday, 6=Sunday
            if current_day not in rule.days_of_week:
                return False
        
        return True


class CustomerSegmentationService:
    """Service for customer segmentation and analysis"""
    
    @staticmethod
    def update_customer_segments():
        """Update customer segments based on defined criteria"""
        
        updated_count = 0
        
        for segment in CustomerSegment.objects.filter(is_active=True):
            # Get customers matching segment criteria
            customers_query = Customer.objects.all()
            
            # Apply segment criteria
            if segment.min_total_spent or segment.max_total_spent:
                profiles = CustomerProfile.objects.all()
                
                if segment.min_total_spent:
                    profiles = profiles.filter(total_spent__gte=segment.min_total_spent)
                if segment.max_total_spent:
                    profiles = profiles.filter(total_spent__lte=segment.max_total_spent)
                
                customers_query = customers_query.filter(
                    id__in=profiles.values_list('customer_id', flat=True)
                )
            
            if segment.min_purchase_frequency:
                profiles = CustomerProfile.objects.filter(
                    purchase_frequency__gte=segment.min_purchase_frequency
                )
                customers_query = customers_query.filter(
                    id__in=profiles.values_list('customer_id', flat=True)
                )
            
            if segment.days_since_last_purchase:
                profiles = CustomerProfile.objects.filter(
                    days_since_last_purchase__lte=segment.days_since_last_purchase
                )
                customers_query = customers_query.filter(
                    id__in=profiles.values_list('customer_id', flat=True)
                )
            
            # Update customer profiles with new segment
            for customer in customers_query:
                try:
                    profile = customer.profile
                    if profile.segment != segment:
                        profile.segment = segment
                        profile.save()
                        updated_count += 1
                except CustomerProfile.DoesNotExist:
                    # Create profile if it doesn't exist
                    CustomerProfile.objects.create(
                        customer=customer,
                        segment=segment
                    )
                    updated_count += 1
        
        logger.info("customer_segments_updated", updated_count=updated_count)
        return updated_count
    
    @staticmethod
    def analyze_customer_behavior(customer_id: int) -> Dict:
        """Analyze individual customer behavior patterns"""
        
        try:
            customer = Customer.objects.get(id=customer_id)
            profile = customer.profile
        except (Customer.DoesNotExist, CustomerProfile.DoesNotExist):
            return {}
        
        # Get transaction history
        transactions = SaleTransaction.objects.filter(
            customer=customer,
            status='completed'
        ).order_by('-sale_date')
        
        if not transactions.exists():
            return {'customer': customer.name, 'transactions': 0}
        
        # Calculate behavior metrics
        total_transactions = transactions.count()
        total_spent = transactions.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        avg_order_value = total_spent / total_transactions if total_transactions > 0 else Decimal('0.00')
        
        # Purchase patterns
        recent_transactions = transactions.filter(
            sale_date__gte=timezone.now() - timedelta(days=90)
        )
        
        # Favorite products
        favorite_products = SaleItem.objects.filter(
            sale_transaction__customer=customer,
            sale_transaction__status='completed'
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_spent=Sum('line_total')
        ).order_by('-total_quantity')[:5]
        
        # Shopping frequency
        if total_transactions > 1:
            first_purchase = transactions.last().sale_date
            days_active = (timezone.now() - first_purchase).days
            purchase_frequency = (total_transactions * 365) / days_active if days_active > 0 else 0
        else:
            purchase_frequency = 0
        
        return {
            'customer': customer.name,
            'customer_tier': profile.tier,
            'total_transactions': total_transactions,
            'total_spent': float(total_spent),
            'average_order_value': float(avg_order_value),
            'purchase_frequency': round(purchase_frequency, 2),
            'days_since_last_purchase': profile.days_since_last_purchase,
            'favorite_products': list(favorite_products),
            'recent_activity': recent_transactions.count(),
            'customer_lifetime_value': float(profile.customer_lifetime_value)
        }


class SalesForecastingService:
    """Advanced sales forecasting and demand planning"""
    
    @staticmethod
    def generate_forecast(store_id: Optional[int] = None, product_id: Optional[int] = None,
                         forecast_days: int = 30, method: str = 'moving_average') -> Dict:
        """Generate sales forecast using specified method"""
        
        # Get historical sales data
        historical_data = SalesForecastingService._get_historical_data(
            store_id, product_id, days=90
        )
        
        if len(historical_data) < 7:
            return {
                'error': 'Insufficient historical data for forecasting',
                'data_points': len(historical_data)
            }
        
        # Apply forecasting method
        if method == 'moving_average':
            forecast_result = SalesForecastingService._moving_average_forecast(
                historical_data, forecast_days
            )
        elif method == 'exponential_smoothing':
            forecast_result = SalesForecastingService._exponential_smoothing_forecast(
                historical_data, forecast_days
            )
        elif method == 'linear_regression':
            forecast_result = SalesForecastingService._linear_regression_forecast(
                historical_data, forecast_days
            )
        else:
            forecast_result = SalesForecastingService._moving_average_forecast(
                historical_data, forecast_days
            )
        
        # Save forecast to database
        forecast_obj = SalesForecast.objects.create(
            store_id=store_id,
            product_id=product_id,
            forecast_method=method,
            forecast_start_date=timezone.now().date(),
            forecast_end_date=timezone.now().date() + timedelta(days=forecast_days),
            historical_data_start=timezone.now().date() - timedelta(days=90),
            predicted_sales_quantity=int(forecast_result['predicted_quantity']),
            predicted_sales_revenue=forecast_result['predicted_revenue'],
            confidence_interval_lower=forecast_result['confidence_lower'],
            confidence_interval_upper=forecast_result['confidence_upper'],
            seasonal_factor=forecast_result.get('seasonal_factor', Decimal('1.000')),
            trend_factor=forecast_result.get('trend_factor', Decimal('1.000'))
        )
        
        logger.info(
            "sales_forecast_generated",
            forecast_id=forecast_obj.id,
            method=method,
            store_id=store_id,
            product_id=product_id,
            predicted_quantity=forecast_result['predicted_quantity']
        )
        
        return forecast_result
    
    @staticmethod
    def _get_historical_data(store_id: Optional[int], product_id: Optional[int], 
                           days: int = 90) -> List[Dict]:
        """Get historical sales data for forecasting"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        if product_id:
            # Product-specific data
            daily_sales = SaleItem.objects.filter(
                sale_transaction__sale_date__date__range=[start_date, end_date],
                sale_transaction__status='completed',
                product_id=product_id
            )
            if store_id:
                daily_sales = daily_sales.filter(store_id=store_id)
            
            # Group by date
            sales_by_date = {}
            for item in daily_sales:
                date_key = item.sale_transaction.sale_date.date()
                if date_key not in sales_by_date:
                    sales_by_date[date_key] = {'quantity': 0, 'revenue': Decimal('0.00')}
                sales_by_date[date_key]['quantity'] += item.quantity
                sales_by_date[date_key]['revenue'] += item.line_total
        
        else:
            # Overall sales data
            transactions = SaleTransaction.objects.filter(
                sale_date__date__range=[start_date, end_date],
                status='completed'
            )
            if store_id:
                transactions = transactions.filter(store_id=store_id)
            
            # Group by date
            sales_by_date = {}
            for transaction in transactions:
                date_key = transaction.sale_date.date()
                if date_key not in sales_by_date:
                    sales_by_date[date_key] = {'quantity': 0, 'revenue': Decimal('0.00')}
                
                # Sum quantities from all items
                total_quantity = transaction.sale_items.aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                
                sales_by_date[date_key]['quantity'] += total_quantity
                sales_by_date[date_key]['revenue'] += transaction.total_amount
        
        # Convert to list format
        historical_data = []
        current_date = start_date
        
        while current_date <= end_date:
            data_point = sales_by_date.get(current_date, {'quantity': 0, 'revenue': Decimal('0.00')})
            historical_data.append({
                'date': current_date,
                'quantity': data_point['quantity'],
                'revenue': float(data_point['revenue'])
            })
            current_date += timedelta(days=1)
        
        return historical_data
    
    @staticmethod
    def _moving_average_forecast(historical_data: List[Dict], forecast_days: int) -> Dict:
        """Simple moving average forecast"""
        
        # Use last 14 days for moving average
        recent_data = historical_data[-14:]
        avg_quantity = sum(point['quantity'] for point in recent_data) / len(recent_data)
        avg_revenue = sum(point['revenue'] for point in recent_data) / len(recent_data)
        
        predicted_quantity = avg_quantity * forecast_days
        predicted_revenue = Decimal(str(avg_revenue * forecast_days))
        
        # Simple confidence interval (±20%)
        confidence_range = predicted_revenue * Decimal('0.2')
        
        return {
            'predicted_quantity': predicted_quantity,
            'predicted_revenue': predicted_revenue,
            'confidence_lower': predicted_revenue - confidence_range,
            'confidence_upper': predicted_revenue + confidence_range,
            'method': 'moving_average',
            'confidence_level': 75.0
        }
    
    @staticmethod
    def _exponential_smoothing_forecast(historical_data: List[Dict], forecast_days: int) -> Dict:
        """Exponential smoothing forecast"""
        
        if len(historical_data) < 7:
            return SalesForecastingService._moving_average_forecast(historical_data, forecast_days)
        
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing parameter
        quantities = [point['quantity'] for point in historical_data]
        revenues = [point['revenue'] for point in historical_data]
        
        # Initialize with first value
        quantity_forecast = quantities[0]
        revenue_forecast = revenues[0]
        
        # Apply exponential smoothing
        for i in range(1, len(quantities)):
            quantity_forecast = alpha * quantities[i] + (1 - alpha) * quantity_forecast
            revenue_forecast = alpha * revenues[i] + (1 - alpha) * revenue_forecast
        
        predicted_quantity = quantity_forecast * forecast_days
        predicted_revenue = Decimal(str(revenue_forecast * forecast_days))
        
        # Confidence interval based on recent variance
        recent_quantities = quantities[-14:]
        variance = np.var(recent_quantities) if len(recent_quantities) > 1 else 0
        confidence_range = predicted_revenue * Decimal(str(min(0.3, variance / max(1, np.mean(recent_quantities)))))
        
        return {
            'predicted_quantity': predicted_quantity,
            'predicted_revenue': predicted_revenue,
            'confidence_lower': predicted_revenue - confidence_range,
            'confidence_upper': predicted_revenue + confidence_range,
            'method': 'exponential_smoothing',
            'confidence_level': 80.0
        }
    
    @staticmethod
    def _linear_regression_forecast(historical_data: List[Dict], forecast_days: int) -> Dict:
        """Linear regression forecast"""
        
        if len(historical_data) < 14:
            return SalesForecastingService._moving_average_forecast(historical_data, forecast_days)
        
        # Prepare data for linear regression
        x_values = list(range(len(historical_data)))
        y_quantities = [point['quantity'] for point in historical_data]
        y_revenues = [point['revenue'] for point in historical_data]
        
        # Calculate linear regression for quantities
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y_qty = sum(y_quantities)
        sum_xy_qty = sum(x * y for x, y in zip(x_values, y_quantities))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept for quantities
        if n * sum_x2 - sum_x * sum_x != 0:
            slope_qty = (n * sum_xy_qty - sum_x * sum_y_qty) / (n * sum_x2 - sum_x * sum_x)
            intercept_qty = (sum_y_qty - slope_qty * sum_x) / n
        else:
            slope_qty = 0
            intercept_qty = sum_y_qty / n if n > 0 else 0
        
        # Calculate linear regression for revenues
        sum_y_rev = sum(y_revenues)
        sum_xy_rev = sum(x * y for x, y in zip(x_values, y_revenues))
        
        if n * sum_x2 - sum_x * sum_x != 0:
            slope_rev = (n * sum_xy_rev - sum_x * sum_y_rev) / (n * sum_x2 - sum_x * sum_x)
            intercept_rev = (sum_y_rev - slope_rev * sum_x) / n
        else:
            slope_rev = 0
            intercept_rev = sum_y_rev / n if n > 0 else 0
        
        # Forecast future values
        future_start = len(historical_data)
        total_predicted_quantity = 0
        total_predicted_revenue = 0
        
        for day in range(forecast_days):
            future_x = future_start + day
            daily_qty = max(0, slope_qty * future_x + intercept_qty)
            daily_rev = max(0, slope_rev * future_x + intercept_rev)
            
            total_predicted_quantity += daily_qty
            total_predicted_revenue += daily_rev
        
        predicted_revenue = Decimal(str(total_predicted_revenue))
        
        # Calculate R-squared for confidence
        y_mean_qty = sum_y_qty / n
        ss_tot = sum((y - y_mean_qty) ** 2 for y in y_quantities)
        ss_res = sum((y - (slope_qty * x + intercept_qty)) ** 2 for x, y in zip(x_values, y_quantities))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        confidence_level = min(95, max(50, r_squared * 100))
        confidence_range = predicted_revenue * Decimal('0.15')  # ±15% based on R-squared
        
        trend_factor = Decimal(str(max(0.5, min(2.0, 1 + slope_qty / max(1, intercept_qty)))))
        
        return {
            'predicted_quantity': total_predicted_quantity,
            'predicted_revenue': predicted_revenue,
            'confidence_lower': predicted_revenue - confidence_range,
            'confidence_upper': predicted_revenue + confidence_range,
            'method': 'linear_regression',
            'confidence_level': confidence_level,
            'trend_factor': trend_factor
        }


class ReturnManagementService:
    """Service for handling returns and refunds"""
    
    @staticmethod
    def process_return(return_id: int, approve: bool = True, 
                      processed_by_id: Optional[int] = None) -> Dict:
        """Process a return request"""
        
        try:
            sales_return = SalesReturn.objects.get(id=return_id)
            
            if sales_return.status != 'pending':
                return {'error': 'Return has already been processed'}
            
            if approve:
                sales_return.status = 'approved'
                
                # Process refund based on method
                if sales_return.refund_method == 'store_credit':
                    # Add store credit to customer
                    ReturnManagementService._add_store_credit(
                        sales_return.customer,
                        sales_return.total_return_amount
                    )
                elif sales_return.refund_method == 'original_payment':
                    # Process refund to original payment method
                    ReturnManagementService._process_payment_refund(sales_return)
                
                # Update customer loyalty points if applicable
                ReturnManagementService._adjust_loyalty_points(sales_return)
                
            else:
                sales_return.status = 'rejected'
            
            sales_return.processed_by_id = processed_by_id
            sales_return.processed_date = timezone.now()
            sales_return.save()
            
            logger.info(
                "return_processed",
                return_id=return_id,
                status=sales_return.status,
                customer_id=sales_return.customer.id,
                amount=float(sales_return.total_return_amount)
            )
            
            return {
                'success': True,
                'return_number': sales_return.return_number,
                'status': sales_return.status,
                'refund_amount': float(sales_return.total_return_amount)
            }
            
        except SalesReturn.DoesNotExist:
            return {'error': 'Return not found'}
        except Exception as e:
            logger.error("return_processing_failed", return_id=return_id, error=str(e))
            return {'error': str(e)}
    
    @staticmethod
    def _add_store_credit(customer: Customer, amount: Decimal):
        """Add store credit to customer account"""
        # This would integrate with a store credit system
        logger.info(
            "store_credit_added",
            customer_id=customer.id,
            amount=float(amount)
        )
    
    @staticmethod
    def _process_payment_refund(sales_return: SalesReturn):
        """Process refund to original payment method"""
        # This would integrate with payment processing system
        logger.info(
            "payment_refund_processed",
            return_id=sales_return.id,
            amount=float(sales_return.total_return_amount)
        )
    
    @staticmethod
    def _adjust_loyalty_points(sales_return: SalesReturn):
        """Adjust customer loyalty points for returned items"""
        
        try:
            loyalty_account = sales_return.customer.loyalty_account
            
            # Calculate points to deduct based on original purchase
            original_transaction = sales_return.original_sale
            points_to_deduct = int(original_transaction.total_amount * loyalty_account.program.points_per_dollar)
            
            if loyalty_account.current_points >= points_to_deduct:
                loyalty_account.current_points -= points_to_deduct
                loyalty_account.save()
                
                # Create loyalty transaction record
                from customers.models import LoyaltyTransaction
                LoyaltyTransaction.objects.create(
                    loyalty_account=loyalty_account,
                    transaction_type='refund',
                    points_change=-points_to_deduct,
                    points_balance_after=loyalty_account.current_points,
                    reference_id=sales_return.return_number,
                    description=f"Points deducted for return {sales_return.return_number}"
                )
                
        except Exception as e:
            logger.warning(
                "loyalty_points_adjustment_failed",
                customer_id=sales_return.customer.id,
                error=str(e)
            )