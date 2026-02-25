from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from core.models import User
from patients.models import Patient
import uuid


class PatientSearchIndex(models.Model):
    """
    Search index for patients to enable fast full-text search.
    This is denormalized data that stays in sync with Patient model.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to original patient
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name='search_index',
        verbose_name=_('patient')
    )
    
    # Denormalized search fields
    mrn = models.CharField(_('MRN'), max_length=20, db_index=True, blank=True, default='')
    national_id = models.CharField(_('national ID'), max_length=20, db_index=True, blank=True, default='')
    
    # Combined name fields for searching
    full_name = models.TextField(_('full name'), db_index=True, blank=True, default='')
    full_name_arabic = models.TextField(_('full name (Arabic)'), blank=True, default='')
    
    # Phone numbers
    phone_mobile = models.CharField(_('mobile phone'), max_length=20, blank=True, default='')
    phone_home = models.CharField(_('home phone'), max_length=20, blank=True, default='')
    
    # Email
    email = models.EmailField(_('email'), blank=True, db_index=True, default='')
    
    # Date of birth
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True, db_index=True)
    
    # Branch (for permission filtering)
    branch_id = models.UUIDField(_('branch ID'), null=True, blank=True, db_index=True)
    
    # Full-text search vector (PostgreSQL specific)
    search_vector = SearchVectorField(null=True)
    
    # Metadata for ranking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('patient search index')
        verbose_name_plural = _('patient search indexes')
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['full_name']),
            models.Index(fields=['mrn', 'branch_id']),
            models.Index(fields=['national_id', 'branch_id']),
        ]
    
    def __str__(self):
        return f"Index for {self.patient.get_full_name() if self.patient else 'Unknown'}"
    
    def update_from_patient(self):
        """
        Update search index from patient data.
        """
        if not self.patient:
            return
            
        self.mrn = self.patient.mrn or ''
        self.national_id = self.patient.national_id or ''
        self.full_name = self.patient.get_full_name() or ''
        self.full_name_arabic = self.patient.get_full_name() or ''
        self.phone_mobile = self.patient.phone_mobile or ''
        self.phone_home = self.patient.phone_home or ''
        self.email = self.patient.email or ''
        self.date_of_birth = self.patient.date_of_birth
        self.branch_id = self.patient.branch_id if self.patient.branch else None


class RecentSearch(models.Model):
    """
    Track recent searches for analytics and quick access.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recent_searches',
        verbose_name=_('user')
    )
    
    query = models.CharField(_('search query'), max_length=255)
    filters = models.JSONField(_('filters'), default=dict, blank=True)
    
    # Result stats
    result_count = models.PositiveIntegerField(_('result count'), default=0)
    
    # Timestamp
    searched_at = models.DateTimeField(_('searched at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('recent search')
        verbose_name_plural = _('recent searches')
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['user', '-searched_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email}: {self.query} ({self.result_count} results)"


class SavedSearch(models.Model):
    """
    Allow users to save frequently used searches.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_searches',
        verbose_name=_('user')
    )
    
    name = models.CharField(_('search name'), max_length=100)
    query = models.CharField(_('search query'), max_length=255)
    filters = models.JSONField(_('filters'), default=dict)
    
    # Optional: notify on new results
    notify_on_new = models.BooleanField(_('notify on new results'), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('saved search')
        verbose_name_plural = _('saved searches')
        unique_together = [['user', 'name']]
    
    def __str__(self):
        return f"{self.user.email}: {self.name}"