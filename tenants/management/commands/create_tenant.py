"""
Management command to create a new tenant with schema and default data.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.models import User
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain, TenantUser
import uuid


class Command(BaseCommand):
    help = 'Create a new tenant with schema and default configuration'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, required=True, help='Tenant name')
        parser.add_argument('--slug', type=str, required=True, help='Tenant slug (URL-friendly)')
        parser.add_argument('--domain', type=str, required=True, help='Primary domain')
        parser.add_argument('--email', type=str, required=True, help='Admin user email')
        parser.add_argument('--password', type=str, help='Admin user password (optional)')
        parser.add_argument('--business-type', type=str, default='retail', help='Business type')
        parser.add_argument('--phone', type=str, help='Contact phone number')
        parser.add_argument('--address', type=str, help='Business address')
        parser.add_argument('--city', type=str, help='City')
        parser.add_argument('--state', type=str, help='State')
        parser.add_argument('--postal-code', type=str, help='Postal code')

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Create tenant
                tenant = Tenant.objects.create(
                    name=options['name'],
                    slug=options['slug'],
                    business_type=options['business_type'],
                    contact_email=options['email'],
                    contact_phone=options.get('phone', ''),
                    address_line1=options.get('address', ''),
                    city=options.get('city', ''),
                    state=options.get('state', ''),
                    postal_code=options.get('postal_code', ''),
                )

                # Create domain
                domain = Domain.objects.create(
                    domain=options['domain'],
                    tenant=tenant,
                    is_primary=True
                )

                # Create admin user if doesn't exist
                user, created = User.objects.get_or_create(
                    username=options['email'],
                    email=options['email'],
                    defaults={
                        'is_staff': True,
                        'is_active': True,
                    }
                )

                if created and options.get('password'):
                    user.set_password(options['password'])
                    user.save()

                # Create tenant-user relationship
                tenant_user = TenantUser.objects.create(
                    user=user,
                    tenant=tenant,
                    role='owner',
                    can_manage_users=True,
                    can_manage_settings=True,
                    can_view_analytics=True,
                    can_manage_inventory=True,
                    can_process_sales=True,
                )

                # Initialize tenant schema with default data
                with schema_context(tenant.schema_name):
                    self.create_default_data(tenant)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created tenant "{tenant.name}" '
                        f'with domain "{domain.domain}" '
                        f'and admin user "{user.email}"'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating tenant: {str(e)}')

    def create_default_data(self, tenant):
        """Create default data for new tenant schema."""
        from settings_app.models import Store
        from products.models import Category
        
        # Create default store
        store = Store.objects.create(
            name=f"{tenant.name} - Main Store",
            store_code="MAIN",
            store_type="main",
            is_active=True,
            currency="USD",
            timezone="UTC",
        )

        # Create default product categories
        categories = [
            "General Merchandise",
            "Electronics",
            "Clothing & Accessories",
            "Food & Beverages",
            "Health & Beauty",
        ]

        for category_name in categories:
            Category.objects.create(
                name=category_name,
                is_active=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Created default data for tenant "{tenant.name}"'
            )
        )