from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Product, ProductExpiration
from inventory.models import StoreInventory
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def check_expiring_products():
    """Check for products nearing expiration and send alerts"""
    try:
        # Check for products expiring in the next 7 days
        expiry_threshold = timezone.now().date() + timedelta(days=7)
        
        expiring_products = ProductExpiration.objects.filter(
            expiration_date__lte=expiry_threshold,
            is_expired=False,
            quantity__gt=0
        ).select_related('product', 'store')
        
        alerts_sent = 0
        for expiration_record in expiring_products:
            days_left = (expiration_record.expiration_date - timezone.now().date()).days
            
            logger.warning(
                "product_expiring_soon",
                product_name=expiration_record.product.name,
                batch_number=expiration_record.batch_number,
                store=expiration_record.store.name,
                days_left=days_left,
                quantity=expiration_record.quantity
            )
            alerts_sent += 1
        
        # Mark expired products
        expired_products = ProductExpiration.objects.filter(
            expiration_date__lt=timezone.now().date(),
            is_expired=False
        )
        expired_count = expired_products.update(is_expired=True)
        
        logger.info(
            "expiration_check_completed",
            expiring_alerts=alerts_sent,
            expired_marked=expired_count
        )
        
        return f"Sent {alerts_sent} expiration alerts, marked {expired_count} as expired"
    
    except Exception as e:
        logger.error("expiration_check_failed", error=str(e))
        raise


@shared_task
def update_product_metrics():
    """Update calculated fields for products"""
    try:
        products_updated = 0
        
        for product in Product.objects.filter(is_active=True):
            # Update total inventory value
            total_stock = product.get_total_stock_across_stores()
            product.total_inventory_value = total_stock * product.average_cost
            
            # Update average cost based on recent stock movements
            recent_movements = product.stock_movements.filter(
                movement_type='purchase',
                movement_date__gte=timezone.now() - timedelta(days=90)
            ).order_by('-movement_date')[:10]
            
            if recent_movements.exists():
                total_cost = sum(movement.unit_cost * abs(movement.quantity) for movement in recent_movements)
                total_quantity = sum(abs(movement.quantity) for movement in recent_movements)
                if total_quantity > 0:
                    product.average_cost = total_cost / total_quantity
            
            product.save(update_fields=['total_inventory_value', 'average_cost'])
            products_updated += 1
        
        logger.info("product_metrics_updated", products_count=products_updated)
        return f"Updated metrics for {products_updated} products"
    
    except Exception as e:
        logger.error("product_metrics_update_failed", error=str(e))
        raise


@shared_task
def generate_low_stock_alerts():
    """Generate alerts for low stock products"""
    try:
        low_stock_products = []
        
        # Check each store's inventory
        for inventory in StoreInventory.objects.select_related('product', 'store'):
            if inventory.quantity_available <= inventory.product.low_stock_threshold:
                low_stock_products.append({
                    'product': inventory.product.name,
                    'store': inventory.store.name,
                    'current_stock': inventory.quantity_available,
                    'threshold': inventory.product.low_stock_threshold
                })
                
                logger.warning(
                    "low_stock_alert",
                    product=inventory.product.name,
                    store=inventory.store.name,
                    current_stock=inventory.quantity_available,
                    threshold=inventory.product.low_stock_threshold
                )
        
        logger.info("low_stock_check_completed", alerts_count=len(low_stock_products))
        return f"Generated {len(low_stock_products)} low stock alerts"
    
    except Exception as e:
        logger.error("low_stock_check_failed", error=str(e))
        raise