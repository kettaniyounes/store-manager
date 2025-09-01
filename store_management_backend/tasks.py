from celery import shared_task
from django.core.management import call_command
from django.conf import settings
import logging
import os
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def cleanup_old_logs():
    """Clean up old log files to prevent disk space issues"""
    try:
        log_dir = settings.BASE_DIR / 'logs'
        if not log_dir.exists():
            return "Log directory does not exist"
        
        cutoff_date = datetime.now() - timedelta(days=30)
        cleaned_files = 0
        
        for log_file in log_dir.glob('*.log*'):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()
                cleaned_files += 1
        
        logger.info("log_cleanup_completed", files_cleaned=cleaned_files)
        return f"Cleaned up {cleaned_files} old log files"
    
    except Exception as e:
        logger.error("log_cleanup_failed", error=str(e))
        raise


@shared_task
def backup_database():
    """Create database backup"""
    try:
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = settings.BASE_DIR / 'backups' / backup_filename
        
        # Create backups directory if it doesn't exist
        backup_path.parent.mkdir(exist_ok=True)
        
        # Create database backup using Django's dumpdata
        call_command('dumpdata', '--output', str(backup_path), '--indent', '2')
        
        logger.info("database_backup_completed", backup_file=backup_filename)
        return f"Database backup created: {backup_filename}"
    
    except Exception as e:
        logger.error("database_backup_failed", error=str(e))
        raise


@shared_task
def optimize_database():
    """Run database optimization tasks"""
    try:
        # Run Django's database optimization commands
        call_command('clearsessions')  # Clear expired sessions
        
        # Additional optimization tasks can be added here
        logger.info("database_optimization_completed")
        return "Database optimization completed"
    
    except Exception as e:
        logger.error("database_optimization_failed", error=str(e))
        raise


@shared_task
def health_check():
    """Perform system health checks"""
    try:
        from django.core.cache import cache
        from django.db import connection
        
        health_status = {
            'database': False,
            'cache': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Test database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status['database'] = True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
        
        # Test cache connection
        try:
            cache.set('health_check', 'ok', 30)
            if cache.get('health_check') == 'ok':
                health_status['cache'] = True
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
        
        logger.info("health_check_completed", status=health_status)
        return health_status
    
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise