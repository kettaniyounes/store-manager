"""
Management command to list all tenants and their status.
"""

from django.core.management.base import BaseCommand
from tenants.models import Tenant, Domain
from django.utils import timezone


class Command(BaseCommand):
    help = 'List all tenants and their status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only', 
            action='store_true',
            help='Show only active tenants'
        )
        parser.add_argument(
            '--detailed', 
            action='store_true',
            help='Show detailed information'
        )

    def handle(self, *args, **options):
        tenants = Tenant.objects.all()
        
        if options['active_only']:
            tenants = tenants.filter(is_active=True)
        
        if not tenants.exists():
            self.stdout.write(self.style.WARNING('No tenants found'))
            return

        self.stdout.write(f'Found {tenants.count()} tenant(s):')
        self.stdout.write('-' * 80)

        for tenant in tenants:
            status = "Active" if tenant.is_active else "Inactive"
            domains = Domain.objects.filter(tenant=tenant)
            primary_domain = domains.filter(is_primary=True).first()
            
            self.stdout.write(
                f'Name: {tenant.name} | Slug: {tenant.slug} | Status: {status}'
            )
            
            if primary_domain:
                self.stdout.write(f'  Primary Domain: {primary_domain.domain}')
            
            if options['detailed']:
                self.stdout.write(f'  ID: {tenant.id}')
                self.stdout.write(f'  Schema: {tenant.schema_name}')
                self.stdout.write(f'  Business Type: {tenant.business_type}')
                self.stdout.write(f'  Subscription: {tenant.subscription_plan}')
                self.stdout.write(f'  Created: {tenant.created_on}')
                self.stdout.write(f'  Contact: {tenant.contact_email}')
                
                if tenant.trial_end_date:
                    trial_status = "Expired" if tenant.trial_end_date < timezone.now() else "Active"
                    self.stdout.write(f'  Trial: {trial_status} (ends: {tenant.trial_end_date})')
                
                all_domains = list(domains.values_list('domain', flat=True))
                if all_domains:
                    self.stdout.write(f'  All Domains: {", ".join(all_domains)}')
            
            self.stdout.write('')