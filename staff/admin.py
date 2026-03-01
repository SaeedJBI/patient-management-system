from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from .models import Staff
from branches.models import Branch


class StaffAdmin(admin.ModelAdmin):
    """
    Admin interface for Staff model - FIXED to show Staff edit page.
    """
    
    # IMPORTANT: First column should link to Staff edit page
    # We'll use 'user' as the first column but make it link to staff edit
    list_display = ('staff_link', 'role', 'branch', 'employee_id', 'specialization', 'is_active', 'assigned_patients_count')
    list_filter = ('role', 'branch', 'is_active', 'department')
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'employee_id', 'specialization'
    )
    ordering = ('branch', 'role', 'user__first_name')
    list_per_page = 25
    
    # Simple fieldsets - exactly like the working version
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'employee_id', 'role', 'branch')
        }),
        ('Professional Info', {
            'fields': ('specialization', 'license_number', 'department')
        }),
        ('Contact', {
            'fields': ('work_phone', 'work_email')
        }),
        ('Status', {
            'fields': ('is_active', 'joined_date', 'left_date')
        }),
        ('Assignments', {  # This is where assigned_patients lives
            'fields': ('assigned_patients',),
            'description': 'Select patients assigned to this staff member. Hold Ctrl/Cmd to select multiple.'
        }),
        ('Audit Info', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # CRITICAL - from working version
    filter_horizontal = ('assigned_patients',)
    
    # Basic readonly fields
    readonly_fields = ('created_at', 'updated_at',)
    
    # Autocomplete for user
    autocomplete_fields = ('user',)
    
    # CUSTOM METHODS
    def staff_link(self, obj):
        """Link to the Staff edit page (NOT User edit page)."""
        if obj and obj.pk:
            url = reverse('admin:staff_staff_change', args=[obj.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return "-"
    staff_link.short_description = _('Staff Member')
    staff_link.admin_order_field = 'user__first_name'
    
    def user_link(self, obj):
        """Separate link to User edit page (optional)."""
        if obj and obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, _('Edit User'))
        return "-"
    user_link.short_description = _('User Account')
    
    def assigned_patients_count(self, obj):
        """Count of assigned patients with link to filtered patient list."""
        if not obj:
            return 0
        count = obj.assigned_patients.count()
        if count > 0:
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


admin.site.register(Staff, StaffAdmin)