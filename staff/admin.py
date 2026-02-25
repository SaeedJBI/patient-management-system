from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from .models import Staff
from branches.models import Branch


class StaffAdmin(admin.ModelAdmin):
    """
    Admin interface for Staff model.
    """
    
    list_display = (
        'user_link', 'role', 'branch', 'employee_id', 
        'specialization', 'is_active', 'assigned_patients_count'
    )
    list_filter = ('role', 'branch', 'is_active', 'department')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'employee_id', 'specialization'
    )
    ordering = ('branch', 'role', 'user__first_name')
    
    fieldsets = (
        (_('User Account'), {
            'fields': ('user', 'employee_id')
        }),
        (_('Role & Branch'), {
            'fields': ('role', 'branch', 'department')
        }),
        (_('Professional Information'), {
            'fields': ('specialization', 'license_number')
        }),
        (_('Contact'), {
            'fields': ('work_phone', 'work_email')
        }),
        (_('Status'), {
            'fields': ('is_active', 'joined_date', 'left_date')
        }),
        (_('Assignments'), {
            'fields': ('assigned_patients',),
            'classes': ('wide',),  # Changed from 'collapse' to 'wide' to make it visible
            'description': _('Select patients assigned to this staff member. Hold Ctrl/Cmd to select multiple.')
        }),
        (_('Audit Information'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)  # Keep audit collapsed
        }),
    )
    
    # These are critical for ManyToMany fields
    filter_horizontal = ('assigned_patients',)
    
    # Add this to make the field more user-friendly
    list_per_page = 25
    
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    # Add these to improve performance with large datasets
    raw_id_fields = ()  # Keep empty since we're using filter_horizontal
    autocomplete_fields = ('user',)  # Add autocomplete for user field
    
    def user_link(self, obj):
        """Link to the associated user in admin."""
        url = reverse('admin:core_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__first_name'
    
    def assigned_patients_count(self, obj):
        """Count of assigned patients with link to filtered patient list."""
        count = obj.assigned_patients.count()
        if count > 0:
            # Create a link to filtered patient list
            patient_ids = ','.join(str(p.id) for p in obj.assigned_patients.all()[:100])
            url = reverse('admin:patients_patient_changelist') + f'?id__in={patient_ids}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    assigned_patients_count.short_description = _('Patients')
    
    def save_model(self, request, obj, form, change):
        """Set created_by automatically."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        return super().get_queryset(request).select_related(
            'user', 'branch', 'created_by'
        ).prefetch_related('assigned_patients')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict branch choices based on user permissions."""
        if db_field.name == 'branch' and not request.user.is_superuser:
            if hasattr(request.user, 'staff_profile'):
                kwargs['queryset'] = Branch.objects.filter(
                    id=request.user.staff_profile.branch.id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields read-only for non-superusers."""
        readonly = list(self.readonly_fields)
        
        if not request.user.is_superuser:
            # Non-superusers cannot change role or branch
            readonly.extend(['role', 'branch'])
            
            # Also make employee_id read-only for non-superusers
            if 'employee_id' not in readonly:
                readonly.append('employee_id')
        
        return readonly
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically adjust fieldsets based on user permissions."""
        fieldsets = super().get_fieldsets(request, obj)
        
        # If user is not superuser and not branch admin, maybe hide audit section
        if not request.user.is_superuser:
            if hasattr(request.user, 'staff_profile'):
                if request.user.staff_profile.role not in ['super_admin', 'branch_admin']:
                    # Filter out audit section for regular staff
                    fieldsets = [fs for fs in fieldsets if fs[0] != _('Audit Information')]
        
        return fieldsets
    
    def has_change_permission(self, request, obj=None):
        """Control who can change staff records."""
        if not obj:
            return super().has_change_permission(request, obj)
        
        # Superuser can change anything
        if request.user.is_superuser:
            return True
        
        # Branch admins can change staff in their branch
        if hasattr(request.user, 'staff_profile'):
            staff = request.user.staff_profile
            if staff.role == 'branch_admin' and obj.branch == staff.branch:
                return True
        
        # Regular staff cannot change other staff records
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers and branch admins can delete staff."""
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'staff_profile'):
            staff = request.user.staff_profile
            if staff.role == 'branch_admin' and obj and obj.branch == staff.branch:
                return True
        
        return False


admin.site.register(Staff, StaffAdmin)