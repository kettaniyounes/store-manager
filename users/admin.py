
# Django Imports
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # Import base UserAdmin
from django.contrib.auth.models import User
from django.conf import settings
from simple_history.admin import SimpleHistoryAdmin
from .models import UserProfile
from django.utils.html import format_html

# Python Imports

# Unregister the default UserAdmin
admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    """
    Inline for UserProfile.
    This prevents deletion of the profile from the User admin and provides a custom verbose name.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin): # Inherit from both BaseUserAdmin and SimpleHistoryAdmin

    inlines = (UserProfileInline,) # Add UserProfileInline
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'date_joined', 'last_login', 'role'
    )
    list_filter = ('is_staff', 'is_active', 'groups', 'profile__role')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        # Removing the separate "Role" fieldset since the role is managed in the inline UserProfile.
    )
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('username',)

    def get_inline_instances(self, request, obj=None): # Override to conditionally show UserProfileInline
        if not obj: # If creating a new user, don't show UserProfileInline (it's created on user save)
            return []
        return super().get_inline_instances(request, obj)

    def role(self, obj): # Method to display role from UserProfile in UserAdmin list
        return obj.profile.get_role_display() if hasattr(obj, 'profile') and obj.profile else '-' # Handle cases where profile might not exist
    role.short_description = 'Role' # Column header for role



@admin.register(UserProfile)
class UserProfileAdmin(SimpleHistoryAdmin):

    list_display = ('user', 'role', 'created_at', 'updated_at')
    list_filter = ('role', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'role') # Search by user details and role
    ordering = ('user__username',)
    fieldsets = (
        ('Profile Information', {
            'fields': ('user', 'role')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'user') # user readonly after creation
    raw_id_fields = ('user',) # raw_id_field for User FK