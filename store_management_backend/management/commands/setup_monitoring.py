from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Setup monitoring and logging directories'

    def handle(self, *args, **options):
        # Create necessary directories
        directories = [
            settings.BASE_DIR / 'logs',
            settings.BASE_DIR / 'backups',
            settings.BASE_DIR / 'monitoring',
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created directory: {directory}')
            )
        
        # Create log files
        log_files = [
            settings.BASE_DIR / 'logs' / 'django.log',
            settings.BASE_DIR / 'logs' / 'celery.log',
            settings.BASE_DIR / 'logs' / 'security.log',
        ]
        
        for log_file in log_files:
            log_file.touch(exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created log file: {log_file}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Monitoring setup completed successfully!')
        )