"""
Management command to run migrations on specific tenant schemas.
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django_tenants.utils import schema_context
from tenants.models import Tenant


class Command(BaseCommand):
    help = 'Run migrations on tenant schemas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant', 
            type=str, 
            help='Tenant slug to migrate (if not provided, migrates all tenants)'
        )
        parser.add_argument(
            '--app', 
            type=str, 
            help='Specific app to migrate'
        )
        parser.add_argument(
            '--fake', 
            action='store_true',
            help='Mark migrations as run without actually running them'
        )

    def handle(self, *args, **options):
        if options['tenant']:
            # Migrate specific tenant
            try:
                tenant = Tenant.objects.get(slug=options['tenant'])
                self.migrate_tenant(tenant, options)
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant with slug "{options["tenant"]}" does not exist')
        else:
            # Migrate all tenants
            tenants = Tenant.objects.filter(is_active=True)
            for tenant in tenants:
                self.migrate_tenant(tenant, options)

    def migrate_tenant(self, tenant, options):
        """Run migrations for a specific tenant."""
        self.stdout.write(f'Migrating tenant: {tenant.name} ({tenant.slug})')
        
        try:
            with schema_context(tenant.schema_name):
                migrate_args = []
                
                if options['app']:
                    migrate_args.append(options['app'])
                
                migrate_kwargs = {}
                if options['fake']:
                    migrate_kwargs['fake'] = True
                
                call_command('migrate', *migrate_args, **migrate_kwargs)
                
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully migrated tenant: {tenant.name}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error migrating tenant {tenant.name}: {str(e)}'
                )
            )