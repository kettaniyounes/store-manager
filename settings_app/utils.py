from django.db import connection, transaction
from django.core.management import call_command
from django.apps import apps
from django.conf import settings
from .models import TenantOrganization
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SchemaManager:
    """Utility class for managing PostgreSQL schemas for multi-tenancy"""
    
    @staticmethod
    def create_tenant_schema(tenant_slug):
        """Create a new tenant schema and run migrations"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            with connection.cursor() as cursor:
                # Create schema
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
                logger.info(f"Created schema: {schema_name}")
                
                # Set search path and run migrations
                cursor.execute(f'SET search_path = "{schema_name}", public')
                
                # Run migrations for the new schema
                SchemaManager.migrate_tenant_schema(schema_name)
                
                return True
        except Exception as e:
            logger.error(f"Error creating schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def migrate_tenant_schema(schema_name):
        """Run migrations for a specific tenant schema"""
        try:
            # Set search path for migrations
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path = "{schema_name}", public')
            
            # Get all apps that need migrations (excluding system apps)
            tenant_apps = [
                'products',
                'sales', 
                'customers',
                'inventory',
                'analytics',
                'suppliers',
                'integrations'
            ]
            
            # Run migrations for each app
            for app_name in tenant_apps:
                try:
                    call_command('migrate', app_name, verbosity=0, interactive=False)
                    logger.info(f"Migrated {app_name} for schema {schema_name}")
                except Exception as e:
                    logger.error(f"Error migrating {app_name} for schema {schema_name}: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Error running migrations for schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def migrate_all_tenants():
        """Run migrations for all active tenant schemas"""
        try:
            tenants = TenantOrganization.objects.filter(status='active')
            success_count = 0
            error_count = 0
            
            for tenant in tenants:
                try:
                    success = SchemaManager.migrate_tenant_schema(tenant.schema_name)
                    if success:
                        success_count += 1
                        logger.info(f"Successfully migrated tenant: {tenant.name}")
                    else:
                        error_count += 1
                        logger.error(f"Failed to migrate tenant: {tenant.name}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error migrating tenant {tenant.name}: {str(e)}")
            
            logger.info(f"Migration completed. Success: {success_count}, Errors: {error_count}")
            return success_count, error_count
            
        except Exception as e:
            logger.error(f"Error during bulk tenant migration: {str(e)}")
            return 0, 1
    
    @staticmethod
    def backup_tenant_schema(tenant_slug, backup_dir=None):
        """Create a backup of a tenant schema"""
        schema_name = f"tenant_{tenant_slug}"
        
        if not backup_dir:
            backup_dir = Path(settings.BASE_DIR) / 'backups' / 'schemas'
        
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"{schema_name}_{timestamp}.sql"
        
        try:
            # Get database connection info
            db_config = settings.DATABASES['default']
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                f"--host={db_config['HOST']}",
                f"--port={db_config['PORT']}",
                f"--username={db_config['USER']}",
                f"--dbname={db_config['NAME']}",
                f"--schema={schema_name}",
                '--no-password',
                '--verbose',
                f"--file={backup_file}"
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            # Execute backup
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully backed up schema {schema_name} to {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"Backup failed for schema {schema_name}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error backing up schema {schema_name}: {str(e)}")
            return None
    
    @staticmethod
    def restore_tenant_schema(tenant_slug, backup_file):
        """Restore a tenant schema from backup"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            # Get database connection info
            db_config = settings.DATABASES['default']
            
            # Drop existing schema first
            SchemaManager.drop_tenant_schema(tenant_slug)
            
            # Build psql command to restore
            cmd = [
                'psql',
                f"--host={db_config['HOST']}",
                f"--port={db_config['PORT']}",
                f"--username={db_config['USER']}",
                f"--dbname={db_config['NAME']}",
                '--no-password',
                f"--file={backup_file}"
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            # Execute restore
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully restored schema {schema_name} from {backup_file}")
                return True
            else:
                logger.error(f"Restore failed for schema {schema_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def archive_tenant_schema(tenant_slug):
        """Archive an inactive tenant schema"""
        try:
            tenant = TenantOrganization.objects.get(slug=tenant_slug)
            
            if tenant.status == 'active':
                logger.warning(f"Cannot archive active tenant: {tenant.name}")
                return False
            
            # Create backup before archiving
            backup_file = SchemaManager.backup_tenant_schema(tenant_slug)
            
            if backup_file:
                # Drop the schema
                success = SchemaManager.drop_tenant_schema(tenant_slug)
                
                if success:
                    # Update tenant status
                    tenant.status = 'archived'
                    tenant.save()
                    
                    logger.info(f"Successfully archived tenant {tenant.name}")
                    return True
                else:
                    logger.error(f"Failed to drop schema for tenant {tenant.name}")
                    return False
            else:
                logger.error(f"Failed to backup tenant {tenant.name} before archiving")
                return False
                
        except TenantOrganization.DoesNotExist:
            logger.error(f"Tenant with slug {tenant_slug} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error archiving tenant {tenant_slug}: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_tenant_schemas():
        """Clean up orphaned schemas and perform maintenance"""
        try:
            # Get all tenant schemas from database
            db_schemas = SchemaManager.get_tenant_schemas()
            
            # Get all tenant organizations
            tenant_slugs = set(
                TenantOrganization.objects.values_list('slug', flat=True)
            )
            
            orphaned_schemas = []
            
            # Find orphaned schemas
            for schema in db_schemas:
                if schema.startswith('tenant_'):
                    slug = schema.replace('tenant_', '')
                    if slug not in tenant_slugs:
                        orphaned_schemas.append(schema)
            
            # Log orphaned schemas
            if orphaned_schemas:
                logger.warning(f"Found orphaned schemas: {orphaned_schemas}")
                
                # Optionally backup and drop orphaned schemas
                for schema in orphaned_schemas:
                    slug = schema.replace('tenant_', '')
                    logger.info(f"Backing up orphaned schema: {schema}")
                    SchemaManager.backup_tenant_schema(slug)
                    
                    # Uncomment to automatically drop orphaned schemas
                    # SchemaManager.drop_tenant_schema(slug)
            
            # Analyze schema sizes
            schema_sizes = SchemaManager.get_schema_sizes()
            for schema, size in schema_sizes.items():
                if schema.startswith('tenant_'):
                    logger.info(f"Schema {schema} size: {size}")
            
            return len(orphaned_schemas)
            
        except Exception as e:
            logger.error(f"Error during schema cleanup: {str(e)}")
            return -1
    
    @staticmethod
    def get_schema_sizes():
        """Get sizes of all tenant schemas"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size
                    FROM pg_tables 
                    WHERE schemaname LIKE 'tenant_%'
                    GROUP BY schemaname
                    ORDER BY sum(pg_total_relation_size(schemaname||'.'||tablename)) DESC
                """)
                
                return dict(cursor.fetchall())
        except Exception as e:
            logger.error(f"Error getting schema sizes: {str(e)}")
            return {}
    
    @staticmethod
    def drop_tenant_schema(tenant_slug):
        """Drop a tenant schema (use with extreme caution)"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                logger.info(f"Dropped schema: {schema_name}")
                return True
        except Exception as e:
            logger.error(f"Error dropping schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def set_tenant_schema(tenant_slug):
        """Set the search path to a specific tenant schema"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path = "{schema_name}", public')
                return True
        except Exception as e:
            logger.error(f"Error setting search path to {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def reset_search_path():
        """Reset search path to default (public schema)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SET search_path = public')
                return True
        except Exception as e:
            logger.error(f"Error resetting search path: {str(e)}")
            return False
    
    @staticmethod
    def get_tenant_schemas():
        """Get list of all tenant schemas"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name LIKE 'tenant_%'
                    ORDER BY schema_name
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting tenant schemas: {str(e)}")
            return []
    
    @staticmethod
    def validate_schema_exists(tenant_slug):
        """Check if a tenant schema exists"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = %s
                    )
                """, [schema_name])
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error validating schema {schema_name}: {str(e)}")
            return False
    
    @staticmethod
    def get_schema_statistics(tenant_slug):
        """Get detailed statistics for a tenant schema"""
        schema_name = f"tenant_{tenant_slug}"
        
        try:
            with connection.cursor() as cursor:
                # Get table count and sizes
                cursor.execute("""
                    SELECT 
                        COUNT(*) as table_count,
                        pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as total_size,
                        pg_size_pretty(sum(pg_relation_size(schemaname||'.'||tablename))::bigint) as data_size
                    FROM pg_tables 
                    WHERE schemaname = %s
                """, [schema_name])
                
                stats = cursor.fetchone()
                
                if stats:
                    return {
                        'schema_name': schema_name,
                        'table_count': stats[0],
                        'total_size': stats[1],
                        'data_size': stats[2]
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting statistics for schema {schema_name}: {str(e)}")
            return None


class TenantContext:
    """Context manager for tenant operations"""
    
    def __init__(self, tenant_slug):
        self.tenant_slug = tenant_slug
        self.schema_name = f"tenant_{tenant_slug}"
        self.original_search_path = None
    
    def __enter__(self):
        # Store original search path
        with connection.cursor() as cursor:
            cursor.execute('SHOW search_path')
            self.original_search_path = cursor.fetchone()[0]
            
            # Set tenant schema
            cursor.execute(f'SET search_path = "{self.schema_name}", public')
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original search path
        if self.original_search_path:
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path = {self.original_search_path}')


class TenantConnectionManager:
    """Manager for tenant-specific database connections"""
    
    _tenant_connections = {}
    
    @classmethod
    def get_tenant_connection(cls, tenant_slug):
        """Get or create a connection for a specific tenant"""
        if tenant_slug not in cls._tenant_connections:
            # For now, we'll use the same connection but with different search paths
            # In production, you might want separate connection pools
            cls._tenant_connections[tenant_slug] = connection
        
        return cls._tenant_connections[tenant_slug]
    
    @classmethod
    def close_tenant_connections(cls):
        """Close all tenant connections"""
        cls._tenant_connections.clear()
    
    @classmethod
    def get_connection_stats(cls):
        """Get statistics about tenant connections"""
        return {
            'active_connections': len(cls._tenant_connections),
            'tenant_slugs': list(cls._tenant_connections.keys())
        }