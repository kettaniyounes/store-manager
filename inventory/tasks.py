from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Sum, F
from .models import StoreInventory
from products.models import Product
from sales.models import SaleItem
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def update_inventory_metrics():
    """Update inventory metrics and calculations"""
    try:
        updated_count = 0
        
        for inventory in StoreInventory.objects.select_related('product', 'store'):
            # Calculate sales velocity (average daily sales over last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            total_sales = SaleItem.objects.filter(
                product=inventory.product,
                store=inventory.store,
                sale_transaction__transaction_date__gte=thirty_days_ago,
                sale_transaction__status='completed'
            ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
            
            inventory.sales_velocity = total_sales / 30.0  # Daily average
            
            # Update available quantity (on_hand - reserved)
            inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
            
            # Calculate inventory turnover
            if inventory.quantity_on_hand > 0:
                inventory.turnover_rate = (total_sales / inventory.quantity_on_hand) * 12  # Annualized
            else:
                inventory.turnover_rate = 0
            
            inventory.save(update_fields=['sales_velocity', 'quantity_available', 'turnover_rate'])
            updated_count += 1
        
        logger.info("inventory_metrics_updated", records_updated=updated_count)
        return f"Updated metrics for {updated_count} inventory records"
    
    except Exception as e:
        logger.error("inventory_metrics_update_failed", error=str(e))
        raise


@shared_task
def calculate_reorder_points():
    """Calculate optimal reorder points based on sales velocity"""
    try:
        updated_count = 0
        
        for inventory in StoreInventory.objects.select_related('product'):
            if inventory.sales_velocity > 0:
                # Calculate reorder point: (average daily sales × lead time) + safety stock
                lead_time_days = inventory.lead_time_days or 7  # Default 7 days
                safety_stock_days = 3  # 3 days safety stock
                
                optimal_reorder_point = int(
                    inventory.sales_velocity * (lead_time_days + safety_stock_days)
                )
                
                # Update reorder point if significantly different
                if abs(inventory.reorder_point - optimal_reorder_point) > 5:
                    inventory.reorder_point = optimal_reorder_point
                    inventory.save(update_fields=['reorder_point'])
                    updated_count += 1
                    
                    logger.info(
                        "reorder_point_updated",
                        product=inventory.product.name,
                        store=inventory.store.name,
                        old_reorder_point=inventory.reorder_point,
                        new_reorder_point=optimal_reorder_point,
                        sales_velocity=inventory.sales_velocity
                    )
        
        logger.info("reorder_points_calculated", updated_count=updated_count)
        return f"Updated reorder points for {updated_count} products"
    
    except Exception as e:
        logger.error("reorder_point_calculation_failed", error=str(e))
        raise


@shared_task
def generate_reorder_suggestions():
    """Generate automatic reorder suggestions"""
    try:
        reorder_suggestions = []
        
        for inventory in StoreInventory.objects.filter(
            quantity_available__lte=F('reorder_point')
        ).select_related('product', 'store'):
            
            suggested_quantity = inventory.reorder_quantity or inventory.product.reorder_quantity
            
            suggestion = {
                'product': inventory.product.name,
                'store': inventory.store.name,
                'current_stock': inventory.quantity_available,
                'reorder_point': inventory.reorder_point,
                'suggested_quantity': suggested_quantity,
                'estimated_cost': suggested_quantity * inventory.product.cost_price
            }
            
            reorder_suggestions.append(suggestion)
            
            logger.info(
                "reorder_suggestion_generated",
                **suggestion
            )
        
        logger.info("reorder_suggestions_completed", suggestions_count=len(reorder_suggestions))
        return f"Generated {len(reorder_suggestions)} reorder suggestions"
    
    except Exception as e:
        logger.error("reorder_suggestions_failed", error=str(e))
        raise