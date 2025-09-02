from django.core.management.base import BaseCommand
from settings_app.models import TenantOrganization
from settings_app.utils import SchemaManager


class Command(BaseCommand):
    help = 'Display statistics for tenant schemas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant slug to show stats for',
            default=None
        )

    def handle(self, *args, **options):
        try:
            if options['tenant']:
                # Show stats for specific tenant
                stats = SchemaManager.get_schema_statistics(options['tenant'])
                
                if stats:
                    self.stdout.write(f"\nTenant Statistics for: {options['tenant']}")
                    self.stdout.write(f"Schema Name: {stats['schema_name']}")
                    self.stdout.write(f"Table Count: {stats['table_count']}")
                    self.stdout.write(f"Total Size: {stats['total_size']}")
                    self.stdout.write(f"Data Size: {stats['data_size']}")
                else:
                    self.stdout.write(
                        self.style.ERROR(f'No statistics found for tenant: {options["tenant"]}')
                    )
            else:
                # Show stats for all tenants
                tenants = TenantOrganization.objects.all()
                schema_sizes = SchemaManager.get_schema_sizes()
                
                self.stdout.write("\nTenant Schema Statistics:")
                self.stdout.write("-" * 50)
                
                for tenant in tenants:
                    size = schema_sizes.get(tenant.schema_name, 'Unknown')
                    self.stdout.write(f"{tenant.name} ({tenant.schema_name}): {size}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting statistics: {str(e)}')
            )