import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_management_backend.settings')

app = Celery('store_management_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'update-inventory-metrics': {
        'task': 'inventory.tasks.update_inventory_metrics',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-expiring-products': {
        'task': 'products.tasks.check_expiring_products',
        'schedule': 3600.0,  # Every hour
    },
    'calculate-reorder-points': {
        'task': 'inventory.tasks.calculate_reorder_points',
        'schedule': 86400.0,  # Daily
    },
    'generate-daily-reports': {
        'task': 'analytics.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Daily at midnight
    },
    'cleanup-old-logs': {
        'task': 'store_management_backend.tasks.cleanup_old_logs',
        'schedule': 604800.0,  # Weekly
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')