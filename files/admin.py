from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import MedicalFile


class MedicalFileAdmin(admin.ModelAdmin):
    """
    Admin interface for MedicalFile model.
    """
    
    list_display = (
        'title', 'patient_link', 'category', 'file_size_display', 
        'uploaded_by', 'created_at', 'is_active', 'download_count'
    )
    list_filter = ('category', 'is_active', 'is_archived', 'created_at')
    search_fields = ('title', 'description', 'patient__first_name', 'patient__last_name')
    readonly_fields = (
        'file_size_display', 'checksum', 'original_filename', 'content_type',
        'file_extension', 'download_count', 'last_accessed', 'created_at', 'updated_at'
    )
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('patient', 'category', 'title', 'description')
        }),
        (_('File'), {
            'fields': ('file', 'file_size_display', 'content_type', 'file_extension')
        }),
        (_('Security'), {
            'fields': ('checksum', 'is_encrypted'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_archived')
        }),
        (_('Access Information'), {
            'fields': ('download_count', 'last_accessed'),
            'classes': ('collapse',)
        }),
        (_('Audit Information'), {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_link(self, obj):
        """Link to patient in admin."""
        from django.urls import reverse
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())
    patient_link.short_description = _('Patient')
    
    def file_size_display(self, obj):
        """Display human-readable file size."""
        return obj.file_size_display
    file_size_display.short_description = _('File Size')
    
    def save_model(self, request, obj, form, change):
        """Set uploaded_by automatically."""
        if not change:  # New object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('patient', 'uploaded_by')


admin.site.register(MedicalFile, MedicalFileAdmin)