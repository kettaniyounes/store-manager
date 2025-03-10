
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords

# Python Imports


class Customer(models.Model):
    
    name = models.CharField(
        max_length=255,
        verbose_name='Customer Name'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,  # Optional: add index if you frequently query by phone
        verbose_name='Phone Number',
        help_text="Customer's phone number (optional)"
    )
    email = models.EmailField(
        blank=True,
        db_index=True,  # Optional: add index if you frequently query by email
        # unique=True,  # Uncomment if emails should be unique
        verbose_name='Email Address',
        help_text="Customer's email address (optional)"
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address',
        help_text="Customer's address (optional)"
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text="Any additional notes about the customer (optional)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['name']  # Default ordering by customer name

    def __str__(self):
        return self.name
