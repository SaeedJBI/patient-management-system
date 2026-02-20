from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import User


class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for User model.
    """
    
    list_display = ('email', 'first_name', 'last_name', 'employee_id', 'is_staff', 'is_active', 'get_local_created_at')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name', 'employee_id')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number', 'employee_id')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'employee_id'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
    
    def get_local_created_at(self, obj):
        """Display created_at in local timezone."""
        if obj.created_at:
            local_time = timezone.localtime(obj.created_at)
            return local_time.strftime("%b. %d, %Y, %I:%M %p")
        return "-"
    get_local_created_at.short_description = 'Created At (Local)'
    get_local_created_at.admin_order_field = 'created_at'


admin.site.register(User, CustomUserAdmin)