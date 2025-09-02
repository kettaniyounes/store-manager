from django.core.management.base import BaseCommand, CommandError
from settings_app.models import TenantOrganization
from settings_app.utils import SchemaManager


class Command(BaseCommand):
    help = 'Backup a tenant schema'

    def add_arguments(self, parser):
        parser.add_argument('tenant_slug', type=str, help='Tenant slug to backup')
        parser.add_argument(
            '--backup-dir',
            type=str,
            help='Directory to store backup files',
            default=None
        )

    def handle(self, *args, **options):
        try:
            # Verify tenant exists
            try:
                tenant = TenantOrganization.objects.get(slug=options['tenant_slug'])
            except TenantOrganization.DoesNotExist:
                raise CommandError(f'Tenant with slug "{options["tenant_slug"]}" does not exist')

            # Create backup
            backup_file = SchemaManager.backup_tenant_schema(
                options['tenant_slug'],
                options.get('backup_dir')
            )

            if backup_file:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully backed up tenant "{tenant.name}" to {backup_file}'
                    )
                )
            else:
                raise CommandError(f'Failed to backup tenant "{tenant.name}"')

        except Exception as e:
            raise CommandError(f'Error during backup: {str(e)}')