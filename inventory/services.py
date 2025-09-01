from django.db.models import Avg, Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import numpy as np
from typing import Dict, List, Tuple, Optional
import structlog
from .models import (
    StoreInventory, SmartReorderRule, 
    BatchLotTracking, SupplierPerformance
)
from products.models import Product
from sales.models import SaleItem

logger = structlog.get_logger(__name__)


class InventoryAnalyticsService:
    """Advanced inventory analytics and forecasting service"""
    
    @staticmethod
    def calculate_sales_velocity(product_id: int, store_id: int, days: int = 30) -> Decimal:
        """Calculate average daily sales velocity"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        total_sales = SaleItem.objects.filter(
            product_id=product_id,
            store_id=store_id,
            sale_transaction__transaction_date__range=[start_date, end_date],
            sale_transaction__status='completed'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        return Decimal(str(total_sales / days))
    
    @staticmethod
    def calculate_demand_variability(product_id: int, store_id: int, days: int = 90) -> Decimal:
        """Calculate demand variability (standard deviation)"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily sales data
        daily_sales = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_total = SaleItem.objects.filter(
                product_id=product_id,
                store_id=store_id,
                sale_transaction__transaction_date=current_date,
                sale_transaction__status='completed'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_sales.append(float(daily_total))
            current_date += timedelta(days=1)
        
        if len(daily_sales) > 1:
            return Decimal(str(np.std(daily_sales)))
        return Decimal('0.00')
    
    @staticmethod
    def predict_demand(product_id: int, store_id: int, forecast_days: int = 30, 
                      method: str = 'moving_average') -> Dict:
        """Predict future demand using various forecasting methods"""
        
        if method == 'moving_average':
            return InventoryAnalyticsService._moving_average_forecast(
                product_id, store_id, forecast_days
            )
        elif method == 'exponential_smoothing':
            return InventoryAnalyticsService._exponential_smoothing_forecast(
                product_id, store_id, forecast_days
            )
        elif method == 'linear_regression':
            return InventoryAnalyticsService._linear_regression_forecast(
                product_id, store_id, forecast_days
            )
        else:
            return InventoryAnalyticsService._moving_average_forecast(
                product_id, store_id, forecast_days
            )
    
    @staticmethod
    def _moving_average_forecast(product_id: int, store_id: int, forecast_days: int) -> Dict:
        """Simple moving average forecast"""
        historical_days = 90
        sales_velocity = InventoryAnalyticsService.calculate_sales_velocity(
            product_id, store_id, historical_days
        )
        
        predicted_demand = sales_velocity * forecast_days
        confidence_level = Decimal('75.00')  # Basic confidence for moving average
        
        return {
            'predicted_demand': predicted_demand,
            'confidence_level': confidence_level,
            'method': 'moving_average',
            'seasonal_factor': Decimal('1.000'),
            'trend_factor': Decimal('1.000')
        }
    
    @staticmethod
    def _exponential_smoothing_forecast(product_id: int, store_id: int, forecast_days: int) -> Dict:
        """Exponential smoothing forecast"""
        # Get historical data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        daily_sales = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_total = SaleItem.objects.filter(
                product_id=product_id,
                store_id=store_id,
                sale_transaction__transaction_date=current_date,
                sale_transaction__status='completed'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_sales.append(float(daily_total))
            current_date += timedelta(days=1)
        
        if len(daily_sales) < 7:
            # Fall back to moving average if insufficient data
            return InventoryAnalyticsService._moving_average_forecast(
                product_id, store_id, forecast_days
            )
        
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing parameter
        forecast = daily_sales[0]
        
        for i in range(1, len(daily_sales)):
            forecast = alpha * daily_sales[i] + (1 - alpha) * forecast
        
        predicted_demand = Decimal(str(forecast * forecast_days))
        confidence_level = Decimal('80.00')
        
        return {
            'predicted_demand': predicted_demand,
            'confidence_level': confidence_level,
            'method': 'exponential_smoothing',
            'seasonal_factor': Decimal('1.000'),
            'trend_factor': Decimal('1.000')
        }
    
    @staticmethod
    def _linear_regression_forecast(product_id: int, store_id: int, forecast_days: int) -> Dict:
        """Linear regression forecast"""
        # Get historical data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        daily_sales = []
        current_date = start_date
        day_index = 0
        
        while current_date <= end_date:
            daily_total = SaleItem.objects.filter(
                product_id=product_id,
                store_id=store_id,
                sale_transaction__transaction_date=current_date,
                sale_transaction__status='completed'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_sales.append((day_index, float(daily_total)))
            current_date += timedelta(days=1)
            day_index += 1
        
        if len(daily_sales) < 14:
            # Fall back to moving average if insufficient data
            return InventoryAnalyticsService._moving_average_forecast(
                product_id, store_id, forecast_days
            )
        
        # Simple linear regression
        x_values = [point[0] for point in daily_sales]
        y_values = [point[1] for point in daily_sales]
        
        n = len(daily_sales)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in daily_sales)
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict future values
        future_day = len(daily_sales)
        daily_forecast = slope * future_day + intercept
        predicted_demand = Decimal(str(max(0, daily_forecast * forecast_days)))
        
        # Calculate R-squared for confidence
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in daily_sales)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        confidence_level = Decimal(str(min(95, max(50, r_squared * 100))))
        
        trend_factor = Decimal(str(max(0.5, min(2.0, 1 + slope / max(1, intercept)))))
        
        return {
            'predicted_demand': predicted_demand,
            'confidence_level': confidence_level,
            'method': 'linear_regression',
            'seasonal_factor': Decimal('1.000'),
            'trend_factor': trend_factor
        }


class SmartReorderService:
    """Service for calculating optimal reorder points and quantities"""
    
    @staticmethod
    def calculate_optimal_reorder_point(store_id: int, product_id: int, 
                                      method: str = 'sales_velocity') -> Dict:
        """Calculate optimal reorder point using specified method"""
        
        try:
            # Get or create reorder rule
            rule, created = SmartReorderRule.objects.get_or_create(
                store_id=store_id,
                product_id=product_id,
                defaults={
                    'calculation_method': method,
                    'lead_time_days': 7,
                    'safety_stock_days': 3,
                    'service_level': Decimal('95.00')
                }
            )
            
            # Calculate sales velocity
            sales_velocity = InventoryAnalyticsService.calculate_sales_velocity(
                product_id, store_id, 30
            )
            
            # Calculate demand variability
            demand_variability = InventoryAnalyticsService.calculate_demand_variability(
                product_id, store_id, 90
            )
            
            # Update rule with current metrics
            rule.sales_velocity = sales_velocity
            rule.demand_variability = demand_variability
            
            if method == 'sales_velocity':
                # Reorder Point = (Average Daily Sales × Lead Time) + Safety Stock
                lead_time_demand = sales_velocity * rule.lead_time_days
                safety_stock = sales_velocity * rule.safety_stock_days
                reorder_point = int(lead_time_demand + safety_stock)
                
                # Order quantity based on EOQ principles
                if sales_velocity > 0:
                    # Simplified EOQ calculation
                    annual_demand = sales_velocity * 365
                    order_quantity = int(max(
                        annual_demand / 12,  # Monthly supply
                        sales_velocity * 7   # Weekly minimum
                    ))
                else:
                    order_quantity = rule.current_order_quantity or 10
            
            elif method == 'min_max':
                # Min-Max method
                min_stock = int(sales_velocity * rule.lead_time_days)
                max_stock = int(min_stock * 2)
                reorder_point = min_stock
                order_quantity = max_stock - min_stock
            
            elif method == 'predictive':
                # Use predictive analytics
                forecast = InventoryAnalyticsService.predict_demand(
                    product_id, store_id, rule.lead_time_days + rule.safety_stock_days
                )
                reorder_point = int(forecast['predicted_demand'])
                order_quantity = int(forecast['predicted_demand'] * 2)
            
            else:
                # Default to current values
                reorder_point = rule.current_reorder_point
                order_quantity = rule.current_order_quantity
            
            # Update rule
            rule.current_reorder_point = reorder_point
            rule.current_order_quantity = order_quantity
            rule.last_calculated = timezone.now()
            rule.save()
            
            logger.info(
                "reorder_point_calculated",
                store_id=store_id,
                product_id=product_id,
                method=method,
                reorder_point=reorder_point,
                order_quantity=order_quantity,
                sales_velocity=float(sales_velocity)
            )
            
            return {
                'reorder_point': reorder_point,
                'order_quantity': order_quantity,
                'sales_velocity': sales_velocity,
                'demand_variability': demand_variability,
                'method': method,
                'confidence': rule.calculation_accuracy or Decimal('75.00')
            }
            
        except Exception as e:
            logger.error(
                "reorder_calculation_failed",
                store_id=store_id,
                product_id=product_id,
                method=method,
                error=str(e)
            )
            raise
    
    @staticmethod
    def generate_reorder_suggestions(store_id: Optional[int] = None) -> List[Dict]:
        """Generate reorder suggestions for products below reorder point"""
        
        query = StoreInventory.objects.filter(
            quantity_available__lte=F('reorder_point')
        ).select_related('product', 'store')
        
        if store_id:
            query = query.filter(store_id=store_id)
        
        suggestions = []
        
        for inventory in query:
            # Get reorder rule
            try:
                rule = SmartReorderRule.objects.get(
                    store=inventory.store,
                    product=inventory.product
                )
                suggested_quantity = rule.current_order_quantity
            except SmartReorderRule.DoesNotExist:
                # Calculate basic suggestion
                sales_velocity = InventoryAnalyticsService.calculate_sales_velocity(
                    inventory.product.id, inventory.store.id, 30
                )
                suggested_quantity = int(max(sales_velocity * 30, 10))  # 30 days supply
            
            # Get best supplier
            best_supplier = SupplierPerformanceService.get_best_supplier(
                inventory.product.id
            )
            
            suggestion = {
                'product': inventory.product,
                'store': inventory.store,
                'current_stock': inventory.quantity_available,
                'reorder_point': inventory.reorder_point,
                'suggested_quantity': suggested_quantity,
                'estimated_cost': suggested_quantity * inventory.product.cost_price,
                'best_supplier': best_supplier,
                'urgency': 'high' if inventory.quantity_available <= 0 else 'medium'
            }
            
            suggestions.append(suggestion)
        
        # Sort by urgency and sales velocity
        suggestions.sort(key=lambda x: (
            x['urgency'] == 'high',
            x['current_stock'] <= 0,
            -float(InventoryAnalyticsService.calculate_sales_velocity(
                x['product'].id, x['store'].id, 7
            ))
        ), reverse=True)
        
        return suggestions


class SupplierPerformanceService:
    """Service for tracking and analyzing supplier performance"""
    
    @staticmethod
    def calculate_supplier_performance(supplier_id: int, product_id: int, 
                                     period_days: int = 90) -> Dict:
        """Calculate comprehensive supplier performance metrics"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        # This would integrate with purchase order system
        # For now, return mock data structure
        performance_data = {
            'on_time_delivery_rate': Decimal('85.5'),
            'quality_rating': 4,
            'price_competitiveness': Decimal('3.8'),
            'communication_rating': 4,
            'average_lead_time': Decimal('5.2'),
            'defect_rate': Decimal('2.1'),
            'total_orders': 15,
            'on_time_deliveries': 13
        }
        
        # Calculate overall score
        weights = {
            'on_time_rate': 0.3,
            'quality': 0.25,
            'price': 0.2,
            'communication': 0.15,
            'defect_rate': 0.1
        }
        
        on_time_score = min(performance_data['on_time_delivery_rate'] / 20, 5)
        defect_score = max(5 - (performance_data['defect_rate'] / 2), 1)
        
        overall_score = (
            weights['on_time_rate'] * on_time_score +
            weights['quality'] * performance_data['quality_rating'] +
            weights['price'] * performance_data['price_competitiveness'] +
            weights['communication'] * performance_data['communication_rating'] +
            weights['defect_rate'] * defect_score
        )
        
        performance_data['overall_score'] = overall_score
        
        return performance_data
    
    @staticmethod
    def get_best_supplier(product_id: int) -> Optional[Dict]:
        """Get the best performing supplier for a product"""
        
        # Get recent performance records
        recent_performances = SupplierPerformance.objects.filter(
            product_id=product_id,
            evaluation_period_end__gte=timezone.now().date() - timedelta(days=180)
        ).select_related('supplier').order_by('-overall_score')
        
        if recent_performances.exists():
            best_performance = recent_performances.first()
            return {
                'supplier': best_performance.supplier,
                'overall_score': best_performance.overall_score,
                'on_time_delivery_rate': best_performance.on_time_delivery_rate,
                'quality_rating': best_performance.quality_rating
            }
        
        return None
    
    @staticmethod
    def update_supplier_ratings():
        """Batch update supplier performance ratings"""
        
        # This would be called periodically to update all supplier ratings
        # Implementation would depend on purchase order and receiving systems
        
        logger.info("supplier_ratings_update_started")
        
        # Mock implementation - would integrate with actual purchase data
        updated_count = 0
        
        logger.info("supplier_ratings_update_completed", updated_count=updated_count)
        
        return updated_count


class BatchLotService:
    """Service for managing batch/lot tracking and FIFO/LIFO operations"""
    
    @staticmethod
    def get_next_batch_for_sale(product_id: int, store_id: int, 
                               quantity_needed: int, method: str = 'fifo') -> List[Dict]:
        """Get next batches to use for sale based on FIFO/LIFO method"""
        
        available_batches = BatchLotTracking.objects.filter(
            product_id=product_id,
            store_id=store_id,
            status='active',
            current_quantity__gt=0
        )
        
        if method == 'fifo':
            # First In, First Out - oldest batches first
            available_batches = available_batches.order_by('received_date', 'expiration_date')
        elif method == 'lifo':
            # Last In, First Out - newest batches first
            available_batches = available_batches.order_by('-received_date')
        elif method == 'fefo':
            # First Expired, First Out - earliest expiration first
            available_batches = available_batches.order_by('expiration_date', 'received_date')
        
        batches_to_use = []
        remaining_quantity = quantity_needed
        
        for batch in available_batches:
            if remaining_quantity <= 0:
                break
            
            available_qty = batch.available_quantity()
            qty_to_take = min(remaining_quantity, available_qty)
            
            if qty_to_take > 0:
                batches_to_use.append({
                    'batch': batch,
                    'quantity': qty_to_take,
                    'unit_cost': batch.unit_cost
                })
                remaining_quantity -= qty_to_take
        
        return batches_to_use
    
    @staticmethod
    def check_expiring_batches(days_ahead: int = 7) -> List[Dict]:
        """Check for batches expiring within specified days"""
        
        expiry_date = timezone.now().date() + timedelta(days=days_ahead)
        
        expiring_batches = BatchLotTracking.objects.filter(
            expiration_date__lte=expiry_date,
            status='active',
            current_quantity__gt=0
        ).select_related('product', 'store').order_by('expiration_date')
        
        alerts = []
        for batch in expiring_batches:
            days_left = (batch.expiration_date - timezone.now().date()).days
            
            alerts.append({
                'batch': batch,
                'days_until_expiration': days_left,
                'current_quantity': batch.current_quantity,
                'total_value': batch.current_quantity * batch.unit_cost,
                'urgency': 'critical' if days_left <= 2 else 'high' if days_left <= 5 else 'medium'
            })
        
        return alerts