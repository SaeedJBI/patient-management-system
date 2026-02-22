from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Patient


class PatientAdmin(admin.ModelAdmin):
    """
    Admin interface for Patient model.
    """
    
    list_display = (
        'mrn', 'get_full_name', 'branch', 'national_id', 
        'gender', 'get_age_display', 'phone_mobile', 'is_active'
    )
    list_filter = ('branch', 'gender', 'is_active', 'blood_type', 'has_allergies', 'has_chronic_conditions')
    search_fields = ('mrn', 'national_id', 'first_name', 'middle_name', 'last_name', 'phone_mobile')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Branch Information'), {
            'fields': ('branch', 'mrn', 'national_id')
        }),
        (_('Personal Information'), {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
                'mother_name',
                ('date_of_birth', 'place_of_birth'),
                ('gender', 'marital_status'),
                'nationality',
            )
        }),
        (_('Contact Information'), {
            'fields': (
                ('phone_mobile', 'phone_home', 'phone_work'),
                'email',
            )
        }),
        (_('Address'), {
            'fields': (
                'address_line1',
                'address_line2',
                ('city', 'state', 'postal_code'),
                'country',
            )
        }),
        (_('Emergency Contact'), {
            'fields': (
                ('emergency_contact_name', 'emergency_contact_relationship'),
                'emergency_contact_phone',
            )
        }),
        (_('Insurance Information'), {
            'fields': (
                ('insurance_provider', 'insurance_policy_number'),
                'insurance_expiry_date',
            ),
            'classes': ('collapse',),
        }),
        (_('Medical Flags'), {
            'fields': (
                ('has_allergies', 'allergy_notes'),
                ('has_chronic_conditions', 'chronic_conditions_notes'),
                'blood_type',
            )
        }),
        (_('Status'), {
            'fields': (
                'is_active',
                ('is_deceased', 'date_of_death'),
                'notes',
            )
        }),
        (_('Audit Information'), {
            'fields': (
                'created_by',
                'updated_by',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('mrn', 'created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_full_name(self, obj):
        """Display full name in list view."""
        return obj.get_full_name()
    get_full_name.short_description = _('Full Name')
    get_full_name.admin_order_field = ('last_name', 'first_name')
    
    def get_age_display(self, obj):
        """Display age in list view."""
        age = obj.get_age()
        return f"{age} years"
    get_age_display.short_description = _('Age')
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by/updated_by."""
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for branch."""
        return super().get_queryset(request).select_related('branch')


admin.site.register(Patient, PatientAdmin)