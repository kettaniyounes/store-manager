
# Django Imports
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings

# Python Imports



class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('inventory', 'Inventory Staff'),
        # Add more roles as needed
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='User'
    ) # One-to-one link to Django User
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='staff',
        verbose_name='Role',
        help_text='User\'s role within the store'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        
        return f"Profile for {self.user.username} - Role: {self.get_role_display()}" # More informative __str__
