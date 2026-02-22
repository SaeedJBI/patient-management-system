from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import User
from branches.models import Branch
import uuid


class Patient(models.Model):
    """
    Patient model representing individuals receiving medical care.
    All patient data is branch-scoped for data isolation.
    """
    
    # Use UUID for public-facing IDs (more secure than sequential numbers)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Branch relationship - EVERY patient belongs to a branch
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.PROTECT,  # Prevent deletion of branch with patients
        related_name='patients',
        verbose_name=_('branch')
    )
    
    # Civil/National ID (important for Middle Eastern context)
    national_id = models.CharField(
        _('national ID'), 
        max_length=20, 
        unique=True,
        validators=[RegexValidator(r'^[0-9]+$', _('Only numbers allowed'))],
        help_text=_('National ID or Civil ID')
    )
    
    # Medical Record Number (auto-generated, but editable if needed)
    mrn = models.CharField(
        _('medical record number'), 
        max_length=20, 
        unique=True,
        help_text=_('Unique medical record number')
    )
    
    # Personal Information
    first_name = models.CharField(_('first name'), max_length=100)
    middle_name = models.CharField(_('middle name'), max_length=100, blank=True)
    last_name = models.CharField(_('last name'), max_length=100)
    mother_name = models.CharField(_('mother\'s name'), max_length=200, blank=True, 
                                   help_text=_('Important for family relations'))
    
    # Date and place of birth
    date_of_birth = models.DateField(_('date of birth'))
    place_of_birth = models.CharField(_('place of birth'), max_length=200, blank=True)
    
    # Gender
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES)
    
    # Marital status
    MARITAL_STATUS_CHOICES = [
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    ]
    marital_status = models.CharField(
        _('marital status'), 
        max_length=20, 
        choices=MARITAL_STATUS_CHOICES,
        blank=True
    )
    
    # Nationality
    nationality = models.CharField(_('nationality'), max_length=100, default='Jordanian')
    
    # Contact Information
    phone_mobile = models.CharField(_('mobile phone'), max_length=20)
    phone_home = models.CharField(_('home phone'), max_length=20, blank=True)
    phone_work = models.CharField(_('work phone'), max_length=20, blank=True)
    
    email = models.EmailField(_('email'), blank=True)
    
    # Address
    address_line1 = models.CharField(_('address line 1'), max_length=255)
    address_line2 = models.CharField(_('address line 2'), max_length=255, blank=True)
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state/province'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20, blank=True)
    country = models.CharField(_('country'), max_length=100, default='Jordan')
    
    # Emergency Contact
    emergency_contact_name = models.CharField(_('emergency contact name'), max_length=200)
    emergency_contact_relationship = models.CharField(_('relationship'), max_length=100)
    emergency_contact_phone = models.CharField(_('emergency contact phone'), max_length=20)
    
    # Insurance Information
    insurance_provider = models.CharField(_('insurance provider'), max_length=200, blank=True)
    insurance_policy_number = models.CharField(_('policy number'), max_length=100, blank=True)
    insurance_expiry_date = models.DateField(_('insurance expiry date'), null=True, blank=True)
    
    # Status flags
    is_active = models.BooleanField(_('active'), default=True, 
                                     help_text=_('Designates whether this patient is currently active.'))
    is_deceased = models.BooleanField(_('deceased'), default=False)
    date_of_death = models.DateField(_('date of death'), null=True, blank=True)
    
    # Important medical flags (non-diagnosis, just alerts)
    has_allergies = models.BooleanField(_('has allergies'), default=False)
    allergy_notes = models.TextField(_('allergy notes'), blank=True)
    has_chronic_conditions = models.BooleanField(_('has chronic conditions'), default=False)
    chronic_conditions_notes = models.TextField(_('chronic conditions notes'), blank=True)
    
    # Blood Type
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('unknown', _('Unknown')),
    ]
    blood_type = models.CharField(_('blood type'), max_length=10, choices=BLOOD_TYPE_CHOICES, default='unknown')
    
    # Notes
    notes = models.TextField(_('general notes'), blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='patients_created',
        verbose_name=_('created by')
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='patients_updated',
        verbose_name=_('updated by')
    )
    
    class Meta:
        verbose_name = _('patient')
        verbose_name_plural = _('patients')
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['mrn']),
            models.Index(fields=['national_id']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['branch', 'is_active']),
            models.Index(fields=['date_of_birth']),
        ]
        # Ensure MRN is unique per branch? Or globally unique?
        # Let's make it globally unique for simplicity
        constraints = [
            models.UniqueConstraint(
                fields=['branch', 'national_id'],
                name='unique_national_id_per_branch'
            ),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.mrn})"
    
    def get_full_name(self):
        """Return the patient's full name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(filter(None, parts))
    
    def get_full_name_arabic_style(self):
        """Return name in Arabic style: First Father Grandfather Last."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(filter(None, parts))
    
    def get_age(self):
        """Calculate patient's age based on date of birth."""
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        # Adjust if birthday hasn't occurred this year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        return age
    
    def save(self, *args, **kwargs):
        """Auto-generate MRN if not provided."""
        if not self.mrn:
            # Generate MRN: BranchCode + Year + 6-digit sequential
            # This is a simple example - you might want a more sophisticated system
            last_patient = Patient.objects.filter(branch=self.branch).order_by('-created_at').first()
            if last_patient and last_patient.mrn.startswith(f"{self.branch.code}{timezone.now().year}"):
                last_number = int(last_patient.mrn[-6:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.mrn = f"{self.branch.code}{timezone.now().year}{new_number:06d}"
        
        super().save(*args, **kwargs)