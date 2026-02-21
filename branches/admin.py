from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """
    Admin interface for Branch model.
    """
    
    list_display = ('name', 'code', 'city', 'state', 'phone', 'is_active', 'get_local_created_at')
    list_filter = ('is_active', 'city', 'state', 'country')
    search_fields = ('name', 'code', 'city', 'address')
    ordering = ('name',)
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'code', 'is_active')
        }),
        (_('Address'), {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        (_('Contact'), {
            'fields': ('phone', 'email')
        }),
        (_('Metadata'), {
            'fields': ('opened_date', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_local_created_at(self, obj):
        if obj.created_at:
            local_time = timezone.localtime(obj.created_at)
            return local_time.strftime("%b. %d, %Y, %I:%M %p")
        return "-"
    get_local_created_at.short_description = _('Created (Local)')
    get_local_created_at.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by when creating a new branch."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)