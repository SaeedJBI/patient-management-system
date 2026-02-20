from django.db import models
from django.core.validators import RegexValidator
from core.models import User  # Import our custom User model


class Branch(models.Model):
    """
    Branch model representing physical locations of the organization.
    
    Every piece of data in the system will be tied to a branch.
    """
    
    # Basic Information
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', 'Only uppercase letters and numbers allowed.')],
        help_text="Unique branch code (e.g., NYC001, LAX002)"
    )
    
    # Contact Information
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=50, default='USA')
    
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Status and Metadata
    is_active = models.BooleanField(default=True)
    opened_date = models.DateField()
    
    # Branch Manager (one staff member as manager)
    # We'll create this relationship after we build the staff app
    # manager = models.ForeignKey('staff.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_branches')
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='branches_created'
    )
    
    class Meta:
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_full_address(self):
        """Return formatted full address."""
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"
    
    def save(self, *args, **kwargs):
        """Ensure branch code is always uppercase."""
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)