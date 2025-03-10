
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords

# Python Imports


class StoreSetting(models.Model):

    KEY_CHOICES = [
        # Define choices for setting keys (you can expand this list)
        ('store_name', 'Store Name'),
        ('default_currency', 'Default Currency'),
        ('tax_rate', 'Default Tax Rate (%)'),
        # Add more setting keys as needed
    ]

    DATA_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('decimal', 'Decimal'),
        ('json', 'JSON'),
    ]

    key = models.CharField(
        max_length=255,
        unique=True,
        choices=KEY_CHOICES,
        verbose_name='Setting Key',
    )
    value = models.TextField(
        verbose_name='Setting Value',
        help_text='Value of the setting. Data type depends on the setting key.',
    )
    data_type = models.CharField(
        max_length=50,
        choices=DATA_TYPE_CHOICES,
        default='string',
        verbose_name='Data Type',
        help_text='Data type of the setting value',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description of what this setting controls (optional)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Store Setting'
        verbose_name_plural = 'Store Settings'
        ordering = ['key']  # Order settings by key

    def __str__(self):
        return f"{self.get_key_display()}: {self.value}"  # Use get_key_display for user-friendly key name