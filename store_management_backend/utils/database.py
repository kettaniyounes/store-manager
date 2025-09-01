from django.db import connection
from django.db import models
from django.core.cache import cache
import structlog

logger = structlog.get_logger(__name__)


class DatabaseOptimizer:
    """Utility class for database optimization tasks"""
    
    @staticmethod
    def analyze_slow_queries():
        """Analyze and log slow queries"""
        try:
            with connection.cursor() as cursor:
                # This would be database-specific
                # For SQLite, we can't get query performance stats
                # For PostgreSQL/MySQL, you would use specific queries
                pass
        except Exception as e:
            logger.error("slow_query_analysis_failed", error=str(e))
    
    @staticmethod
    def get_database_stats():
        """Get database statistics"""
        try:
            with connection.cursor() as cursor:
                # Get table sizes and row counts
                cursor.execute("""
                    SELECT name, COUNT(*) as row_count 
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()
                
                stats = {}
                for table_name, _ in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    stats[table_name] = {'row_count': row_count}
                
                return stats
        except Exception as e:
            logger.error("database_stats_failed", error=str(e))
            return {}
    
    @staticmethod
    def optimize_tables():
        """Optimize database tables"""
        try:
            with connection.cursor() as cursor:
                # For SQLite, run VACUUM to optimize
                cursor.execute("VACUUM")
                logger.info("database_vacuum_completed")
        except Exception as e:
            logger.error("table_optimization_failed", error=str(e))


class CacheManager:
    """Utility class for cache management"""
    
    @staticmethod
    def warm_cache():
        """Warm up frequently accessed cache entries"""
        try:
            from products.models import Product
            from inventory.models import StoreInventory
            
            # Cache active products
            active_products = list(Product.objects.filter(is_active=True).values_list('id', flat=True))
            cache.set('active_products', active_products, 3600)
            
            # Cache low stock items
            low_stock_items = list(
                StoreInventory.objects.filter(
                    quantity_available__lte=models.F('reorder_point')
                ).values_list('id', flat=True)
            )
            cache.set('low_stock_items', low_stock_items, 1800)
            
            logger.info("cache_warmed", products_cached=len(active_products), low_stock_cached=len(low_stock_items))
            
        except Exception as e:
            logger.error("cache_warming_failed", error=str(e))
    
    @staticmethod
    def clear_expired_cache():
        """Clear expired cache entries"""
        try:
            # This would be Redis-specific
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            # Get all keys and check expiration
            keys = redis_conn.keys("*")
            expired_keys = []
            
            for key in keys:
                ttl = redis_conn.ttl(key)
                if ttl == -1:  # No expiration set
                    continue
                elif ttl == -2:  # Key doesn't exist
                    expired_keys.append(key)
            
            if expired_keys:
                redis_conn.delete(*expired_keys)
                logger.info("expired_cache_cleared", keys_cleared=len(expired_keys))
            
        except Exception as e:
            logger.error("cache_cleanup_failed", error=str(e))