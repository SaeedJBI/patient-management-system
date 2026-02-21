from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from core.models import User


class Branch(models.Model):
    """
    Branch model representing physical locations.
    """
    
    name = models.CharField(_('name'), max_length=100, unique=True)
    code = models.CharField(
        _('code'),
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', _('Only uppercase letters and numbers allowed.'))],
        help_text=_("Unique branch code (e.g., NYC001, LAX002)")
    )
    
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=50)
    state = models.CharField(_('state'), max_length=50)
    postal_code = models.CharField(_('postal code'), max_length=20)
    country = models.CharField(_('country'), max_length=50, default='USA')
    
    phone = models.CharField(_('phone'), max_length=20)
    email = models.EmailField(_('email'), blank=True)
    
    is_active = models.BooleanField(_('is active'), default=True)
    opened_date = models.DateField(_('opened date'))
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='branches_created',
        verbose_name=_('created by')
    )
    
    class Meta:
        verbose_name = _('Branch')
        verbose_name_plural = _('Branches')
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"
    
    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)