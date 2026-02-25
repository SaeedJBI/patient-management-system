from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class UserManager(BaseUserManager):
    """Custom manager for User model where email is the unique identifier."""
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        # Set default values for required fields if not provided
        if 'first_name' not in extra_fields or not extra_fields.get('first_name'):
            extra_fields['first_name'] = 'Admin'
        if 'last_name' not in extra_fields or not extra_fields.get('last_name'):
            extra_fields['last_name'] = 'User'
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User Model for PMS.
    Email is used as the unique identifier instead of username.
    """
    
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(_('phone number'), max_length=15, blank=True)
    employee_id = models.CharField(_('employee id'), max_length=20, unique=True, null=True, blank=True)
    language = models.CharField(
        _('language'),
        max_length=10,
        choices=settings.LANGUAGES,
        default='en'
    )
    
    # Make username optional and non-unique since we're not using it
    username = models.CharField(
        _('username'),
        max_length=150,
        blank=True,
        null=True,
        unique=False,
        help_text=_('Optional. Not used for login.'),
    )
    
    # Audit fields
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    # Use the custom manager
    objects = UserManager()
    
    # Set email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  # These are required when creating a superuser
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the full name of the user."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email
    
    def get_short_name(self):
        """Return the short name of the user."""
        return self.first_name or self.email.split('@')[0]
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure username is set (even though we don't use it).
        Some Django internals still expect username to exist.
        """
        if not self.username and self.email:
            # Create a simple username from email (remove @ and domain)
            self.username = self.email.split('@')[0][:150]
        super().save(*args, **kwargs)