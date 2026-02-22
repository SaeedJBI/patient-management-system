import os
import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.conf import settings
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
        ('lab_report', _('Lab Report')),
        ('xray', _('X-Ray / Radiology')),
        ('prescription', _('Prescription')),
        ('identification', _('Identification Document')),
        ('insurance', _('Insurance Document')),
        ('consent', _('Consent Form')),
        ('medical_history', _('Medical History')),
        ('other', _('Other')),
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
    
    # File metadata - make these nullable temporarily for the fix
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
    
    def save(self, *args, **kwargs):
        """Populate metadata fields when saving."""
        # First, save without metadata to ensure file is stored
        if self.file and not self.pk:  # New file upload
            # Store original filename
            self.original_filename = self.file.name
            
            # Get file extension
            self.file_extension = os.path.splitext(self.file.name)[1].lower().lstrip('.')
            
            # We need to save first so the file is actually stored
            super().save(*args, **kwargs)
            
            # Now that file is saved, we can access its properties
            if self.file and hasattr(self.file, 'size'):
                self.file_size = self.file.size
            
            if self.file and hasattr(self.file.file, 'content_type'):
                self.content_type = self.file.file.content_type
            
            # Calculate checksum
            if self.file:
                sha256 = hashlib.sha256()
                self.file.seek(0)  # Go to beginning of file
                for chunk in self.file.chunks():
                    sha256.update(chunk)
                self.checksum = sha256.hexdigest()
                self.file.seek(0)  # Reset for future reads
            
            # Update with metadata
            super().save(update_fields=['file_size', 'content_type', 'checksum'])
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
    
    @property
    def file_size_display(self):
        """Return human-readable file size."""
        if not self.file_size:
            return "Unknown"
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def branch(self):
        """Get branch through patient (for permissions)."""
        return self.patient.branch