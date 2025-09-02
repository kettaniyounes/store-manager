from django.core.management.base import BaseCommand, CommandError
from settings_app.models import TenantOrganization
from settings_app.utils import SchemaManager


class Command(BaseCommand):
    help = 'Run migrations for a specific tenant or all tenants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant slug to migrate (if not provided, migrates all tenants)',
            default=None
        )

    def handle(self, *args, **options):
        try:
            if options['tenant']:
                # Migrate specific tenant
                try:
                    tenant = TenantOrganization.objects.get(slug=options['tenant'])
                    success = SchemaManager.migrate_tenant_schema(tenant.schema_name)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully migrated tenant "{tenant.name}"'
                            )
                        )
                    else:
                        raise CommandError(f'Failed to migrate tenant "{tenant.name}"')
                        
                except TenantOrganization.DoesNotExist:
                    raise CommandError(f'Tenant with slug "{options["tenant"]}" does not exist')
            else:
                # Migrate all tenants
                tenants = TenantOrganization.objects.filter(status='active')
                
                for tenant in tenants:
                    success = SchemaManager.migrate_tenant_schema(tenant.schema_name)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully migrated tenant "{tenant.name}"'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to migrate tenant "{tenant.name}"'
                            )
                        )

        except Exception as e:
            raise CommandError(f'Error during migration: {str(e)}')