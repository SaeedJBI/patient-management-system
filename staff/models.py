from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from core.models import User
from branches.models import Branch
from patients.models import Patient


# Role definitions based on your requirements
ROLE_CHOICES = [
    ('doctor', _('Doctor')),
    ('pharmacist', _('Pharmacist')),
    ('nutritionist', _('Nutritionist')),
    ('receptionist', _('Receptionist')),
    ('branch_admin', _('Branch Admin')),
    ('super_admin', _('Super Admin')),
]

# File categories each role can upload
ROLE_CATEGORY_PERMISSIONS = {
    'doctor': ['medical_report', 'prescription', 'lab_result', 'imaging', 'note'],
    'pharmacist': ['prescription', 'receipt', 'medicine_info', 'note'],
    'nutritionist': ['nutrition_plan', 'diet_program', 'food_diary', 'note'],
    'receptionist': ['appointment', 'visit_note', 'consent', 'note'],
    'branch_admin': ['all'],  # Can upload anything in their branch
    'super_admin': ['all'],   # Can upload anything anywhere
}

# View permissions (what each role can see)
ROLE_VIEW_PERMISSIONS = {
    'doctor': ['all_patient_files', 'medical_history', 'lab_results'],
    'pharmacist': ['medication_history', 'prescriptions', 'receipts'],
    'nutritionist': ['nutrition_history', 'diet_plans'],
    'receptionist': ['appointments', 'demographics_readonly'],
    'branch_admin': ['all_in_branch'],
    'super_admin': ['all'],
}


class Staff(models.Model):
    """
    Staff profile extending the User model.
    Links a user to a branch and role with specific permissions.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile',
        verbose_name=_('user')
    )
    
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='staff_members',
        verbose_name=_('branch')
    )
    
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES
    )
    
    employee_id = models.CharField(
        _('employee ID'),
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', _('Only uppercase letters and numbers'))]
    )
    
    # Professional information
    specialization = models.CharField(
        _('specialization'),
        max_length=100,
        blank=True,
        help_text=_('e.g., Cardiology, Clinical Pharmacy, Sports Nutrition')
    )
    
    license_number = models.CharField(
        _('license number'),
        max_length=50,
        blank=True
    )
    
    department = models.CharField(
        _('department/unit'),
        max_length=100,
        blank=True
    )
    
    # Patients assigned to this staff member
    assigned_patients = models.ManyToManyField(
        'patients.Patient',  # Note: using string reference
        blank=True,
        related_name='assigned_staff',
        verbose_name=_('assigned patients')
    )
    
    # Contact info (work)
    work_phone = models.CharField(_('work phone'), max_length=20, blank=True)
    work_email = models.EmailField(_('work email'), blank=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    joined_date = models.DateField(_('joined date'))
    left_date = models.DateField(_('left date'), null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='staff_created',
        verbose_name=_('created by')
    )
    
    class Meta:
        verbose_name = _('staff')
        verbose_name_plural = _('staff members')
        unique_together = [
            ['branch', 'employee_id'],
            ['user', 'branch'],  # User can only be in one branch
        ]
        indexes = [
            models.Index(fields=['branch', 'role']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['employee_id']),
        ]
        permissions = [
            ("can_manage_staff", _("Can manage staff members")),
            ("can_assign_patients", _("Can assign patients to staff")),
            ("can_view_all_branches", _("Can view all branches data")),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()} ({self.branch.code})"
    
    def save(self, *args, **kwargs):
        """Ensure employee_id is uppercase."""
        if self.employee_id:
            self.employee_id = self.employee_id.upper()
        super().save(*args, **kwargs)
    
    def can_upload_category(self, category):
        """
        Check if this staff member can upload files of a given category.
        """
        if self.role == 'super_admin' or self.role == 'branch_admin':
            return True
        
        allowed = ROLE_CATEGORY_PERMISSIONS.get(self.role, [])
        return category in allowed or 'all' in allowed
    
    def can_view_patient(self, patient):
        """
        Check if this staff member can view a specific patient.
        """
        # Super admin can view all
        if self.role == 'super_admin':
            return True
        
        # Branch admin can view all patients in their branch
        if self.role == 'branch_admin' and patient.branch == self.branch:
            return True
        
        # Regular staff can only view assigned patients
        return self.assigned_patients.filter(id=patient.id).exists()
    
    def can_edit_demographics(self):
        """
        Check if this staff member can edit patient demographics.
        """
        # Only admins can edit demographics
        return self.role in ['branch_admin', 'super_admin']
    
    def get_visible_patients(self):
        """
        Get queryset of patients this staff member can see.
        """
        if self.role == 'super_admin':
            return Patient.objects.all()
        
        if self.role == 'branch_admin':
            return Patient.objects.filter(branch=self.branch)
        
        return self.assigned_patients.all()
    
    def assign_patient(self, patient):
        """
        Assign a patient to this staff member with validation.
        """
        if patient.branch != self.branch:
            raise ValueError(_("Cannot assign patient from different branch"))
        
        self.assigned_patients.add(patient)
    
    def unassign_patient(self, patient):
        """
        Remove a patient from this staff member's assignments.
        """
        self.assigned_patients.remove(patient)


# Signal to ensure superuser has staff profile
@receiver(post_save, sender=User)
def create_staff_profile_for_superuser(sender, instance, created, **kwargs):
    """
    Automatically create staff profile for superusers if they don't have one.
    """
    if instance.is_superuser and not hasattr(instance, 'staff_profile'):
        # Get first branch or create a system branch
        from branches.models import Branch  # Import inside function to avoid circular import
        from django.utils import timezone
        
        branch = Branch.objects.first()
        if not branch:
            # Create a system branch if none exists
            branch = Branch.objects.create(
                name='System Branch',
                code='SYS',
                address='System',
                city='System',
                state='System',
                postal_code='00000',
                country='System',
                phone='0000000000',
                email='system@hospital.local',
                opened_date=timezone.now().date(),
                is_active=True,
                created_by=instance  # Set created_by to the superuser
            )
        
        # Create staff profile
        Staff.objects.create(
            user=instance,
            branch=branch,
            role='super_admin',
            employee_id=f"SUPER{instance.id:06d}",
            joined_date=timezone.now().date(),
            created_by=instance,
            is_active=True
        )