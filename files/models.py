import os
import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from core.models import User
from patients.models import Patient
import hashlib


def patient_file_path(instance, filename):
    """
    Generate file path: patient_<uuid>/<category>/<year>/<month>/<filename>
    """
    ext = filename.split('.')[-1]
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join(
        'patient_files',
        str(instance.patient.id),
        instance.category,
        str(timezone.now().year),
        str(timezone.now().month).zfill(2),
        safe_filename
    )


class MedicalFile(models.Model):
    """
    Model for storing medical files securely.
    """
    
    CATEGORY_CHOICES = [
        # Doctors - Medical reports only
        ('medical_report', _('Medical Report')),
        
        # Pharmacists - Medicine receipts/prescriptions
        ('prescription', _('Prescription')),
        
        # Nutritionists - Diet programs
        ('diet_program', _('Diet Program')),
        
        # Receptionists - Appointments and notes
        ('appointment', _('Appointment')),
        
        # Finance - Bills
        ('bill_monthly', _('Monthly Bill')),
        ('bill_yearly', _('Yearly Bill')),
        
        # General - Notes (everyone can upload notes)
        ('note', _('General Note')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_files',
        verbose_name=_('patient')
    )
    
    file = models.FileField(
        _('file'),
        upload_to=patient_file_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'pdf', 'doc', 'docx', 'xls', 'xlsx',
                    'jpg', 'jpeg', 'png', 'gif', 'tiff',
                    'txt', 'csv'
                ]
            )
        ],
        help_text=_('Allowed file types: PDF, Word, Excel, images, text')
    )
    
    category = models.CharField(
        _('category'),
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    
    # File metadata
    original_filename = models.CharField(_('original filename'), max_length=255, blank=True)
    file_size = models.PositiveIntegerField(_('file size (bytes)'), null=True, blank=True)
    content_type = models.CharField(_('content type'), max_length=100, blank=True)
    file_extension = models.CharField(_('file extension'), max_length=20, blank=True)
    
    checksum = models.CharField(
        _('checksum'),
        max_length=64,
        blank=True,
        help_text=_('SHA-256 checksum for file integrity')
    )
    
    is_encrypted = models.BooleanField(_('encrypted'), default=False, editable=False)
    is_active = models.BooleanField(_('active'), default=True)
    is_archived = models.BooleanField(_('archived'), default=False)
    
    download_count = models.PositiveIntegerField(_('download count'), default=0, editable=False)
    last_accessed = models.DateTimeField(_('last accessed'), null=True, blank=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files',
        verbose_name=_('uploaded by')
    )
    
    class Meta:
        verbose_name = _('medical file')
        verbose_name_plural = _('medical files')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'category']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['checksum']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.patient.get_full_name()}"
    
    def clean(self):
        """
        Validate file upload permissions.
        This is called automatically by Django forms and model validation.
        """
        # Skip validation in admin or for superusers (can be set in views)
        if hasattr(self, '_skip_validation') and self._skip_validation:
            return
        
        # Skip validation if no uploader (shouldn't happen)
        if not self.uploaded_by:
            return
        
        # Superuser can do anything
        if self.uploaded_by.is_superuser:
            return
        
        # Check if uploader has staff profile
        if not hasattr(self.uploaded_by, 'staff_profile'):
            raise ValidationError(_(
                'User does not have a staff profile. '
                'Only staff members can upload files.'
            ))
        
        staff = self.uploaded_by.staff_profile
        
        # Check if staff is active
        if not staff.is_active:
            raise ValidationError(_(
                'Your staff account is inactive. '
                'Please contact your administrator.'
            ))
        
        # Check branch match
        if self.patient.branch != staff.branch:
            raise ValidationError(_(
                'Cannot upload files for patients in other branches. '
                f'Your branch: {staff.branch.code}, Patient branch: {self.patient.branch.code}'
            ))
        
        # Check patient assignment
        if not staff.can_view_patient(self.patient):
            raise ValidationError(_(
                'This patient is not assigned to you. '
                'You can only upload files for patients assigned to your care.'
            ))
        
        # Check category permission
        if not staff.can_upload_category(self.category):
            allowed = self.get_allowed_categories_for_staff(staff)
            raise ValidationError(_(
                f'Your role ({staff.get_role_display()}) cannot upload files '
                f'of type: {self.get_category_display()}. '
                f'Allowed types: {", ".join(allowed)}'
            ))
    
    def save(self, *args, **kwargs):
        """Populate metadata fields and validate permissions when saving."""
        # Run validation
        self.clean()
        
        # Handle file uploads
        if self.file:
            # ALWAYS extract extension from the filename
            filename = self.file.name
            if '.' in filename:
                self.file_extension = filename.split('.')[-1].lower()
            
            # Store original filename if not already set
            if not self.original_filename:
                self.original_filename = self.file.name
        
        # Handle new file uploads
        if self.file and not self.pk:  # New file upload
            # Save first to ensure file is stored
            super().save(*args, **kwargs)
            
            # Now get all metadata from the saved file
            update_fields = []
            
            # Get file size
            if hasattr(self.file, 'size'):
                self.file_size = self.file.size
                update_fields.append('file_size')
            
            # Get content type
            if hasattr(self.file.file, 'content_type'):
                self.content_type = self.file.file.content_type
                update_fields.append('content_type')
            
            # Calculate checksum
            sha256 = hashlib.sha256()
            self.file.seek(0)
            for chunk in self.file.chunks():
                sha256.update(chunk)
            self.checksum = sha256.hexdigest()
            self.file.seek(0)
            update_fields.append('checksum')
            
            # Add other fields if they were set
            if self.file_extension:
                update_fields.append('file_extension')
            if self.original_filename:
                update_fields.append('original_filename')
            
            # Update with metadata
            if update_fields:
                super().save(update_fields=update_fields)
        else:
            super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete the actual file when the model is deleted."""
        if self.file:
            storage = self.file.storage
            if storage.exists(self.file.name):
                storage.delete(self.file.name)
        super().delete(*args, **kwargs)
    
    def increment_download_count(self):
        """Track file downloads."""
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])
    
    def get_allowed_categories_for_staff(self, staff=None):
        """
        Get list of categories this staff member can upload.
        """
        if staff is None and self.uploaded_by:
            if hasattr(self.uploaded_by, 'staff_profile'):
                staff = self.uploaded_by.staff_profile
        
        if staff:
            from staff.models import ROLE_CATEGORY_PERMISSIONS
            perms = ROLE_CATEGORY_PERMISSIONS.get(staff.role, [])
            if 'all' in perms:
                return [cat[0] for cat in self.CATEGORY_CHOICES]
            return perms
        return []
    
    @property
    def file_size_display(self):
        """Return human-readable file size."""
        if self.file_size is None:
            # Try to get size from file if not in database
            if self.file and hasattr(self.file, 'size'):
                try:
                    self.file_size = self.file.size
                    self.save(update_fields=['file_size'])
                except:
                    return _("Unknown")
            else:
                return _("Unknown")
        
        size = self.file_size
        for unit in [_('B'), _('KB'), _('MB'), _('GB')]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def branch(self):
        """Get branch through patient (for permissions)."""
        return self.patient.branch
    
    @property
    def is_image(self):
        """Check if file is an image."""
        return self.file_extension.lower() in ['jpg', 'jpeg', 'png', 'gif', 'tiff']
    
    @property
    def is_pdf(self):
        """Check if file is a PDF."""
        return self.file_extension.lower() == 'pdf'
    
    @property
    def is_document(self):
        """Check if file is a document (Word, Excel, etc.)."""
        return self.file_extension.lower() in ['doc', 'docx', 'xls', 'xlsx', 'txt', 'csv']
    
    @property
    def can_preview(self):
        """Check if file can be previewed in browser."""
        previewable_extensions = ['jpg', 'jpeg', 'png', 'gif', 'tiff', 'pdf', 'txt', 'csv']
        return self.file_extension.lower() in previewable_extensions