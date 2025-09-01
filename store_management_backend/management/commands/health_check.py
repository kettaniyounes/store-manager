from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis
import json


class Command(BaseCommand):
    help = 'Perform comprehensive health check'

    def handle(self, *args, **options):
        health_status = {
            'database': self.check_database(),
            'cache': self.check_cache(),
            'redis': self.check_redis(),
            'disk_space': self.check_disk_space(),
        }
        
        # Output results
        self.stdout.write(json.dumps(health_status, indent=2))
        
        # Exit with error code if any check failed
        if not all(health_status.values()):
            exit(1)

    def check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(
                self.style.SUCCESS('✓ Database connection: OK')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Database connection: FAILED - {e}')
            )
            return False

    def check_cache(self):
        try:
            cache.set('health_check', 'ok', 30)
            if cache.get('health_check') == 'ok':
                self.stdout.write(
                    self.style.SUCCESS('✓ Cache system: OK')
                )
                return True
            else:
                raise Exception("Cache test failed")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Cache system: FAILED - {e}')
            )
            return False

    def check_redis(self):
        try:
            redis_client = redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            self.stdout.write(
                self.style.SUCCESS('✓ Redis connection: OK')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Redis connection: FAILED - {e}')
            )
            return False

    def check_disk_space(self):
        try:
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            free_percent = (free / total) * 100
            
            if free_percent > 10:  # More than 10% free space
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Disk space: OK ({free_percent:.1f}% free)')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Disk space: LOW ({free_percent:.1f}% free)')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Disk space check: FAILED - {e}')
            )
            return False