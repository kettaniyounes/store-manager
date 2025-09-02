from django.core.management.base import BaseCommand
from settings_app.utils import SchemaManager


class Command(BaseCommand):
    help = 'Clean up orphaned tenant schemas and perform maintenance'

    def handle(self, *args, **options):
        try:
            orphaned_count = SchemaManager.cleanup_tenant_schemas()
            
            if orphaned_count >= 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Schema cleanup completed. Found {orphaned_count} orphaned schemas.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Schema cleanup failed.')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during cleanup: {str(e)}')
            )