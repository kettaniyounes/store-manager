from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from settings_app.models import TenantOrganization
from settings_app.utils import SchemaManager


class Command(BaseCommand):
    help = 'Create a new tenant organization with schema'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Tenant organization name')
        parser.add_argument('slug', type=str, help='Tenant slug (used for schema naming)')
        parser.add_argument('owner_email', type=str, help='Email of the tenant owner')
        parser.add_argument(
            '--domain',
            type=str,
            help='Custom domain for the tenant',
            default=None
        )
        parser.add_argument(
            '--max-users',
            type=int,
            help='Maximum number of users allowed',
            default=10
        )
        parser.add_argument(
            '--max-stores',
            type=int,
            help='Maximum number of stores allowed',
            default=5
        )

    def handle(self, *args, **options):
        try:
            # Get or create owner user
            try:
                owner = User.objects.get(email=options['owner_email'])
            except User.DoesNotExist:
                raise CommandError(f"User with email {options['owner_email']} does not exist")

            # Create tenant organization
            tenant = TenantOrganization.objects.create(
                name=options['name'],
                slug=options['slug'],
                owner=owner,
                domain=options.get('domain'),
                max_users=options['max_users'],
                max_stores=options['max_stores'],
                status='active'
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created tenant "{tenant.name}" with schema "{tenant.schema_name}"'
                )
            )

        except Exception as e:
            raise CommandError(f'Error creating tenant: {str(e)}')