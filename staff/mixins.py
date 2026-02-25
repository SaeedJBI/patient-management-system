from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from patients.models import Patient


class StaffPermissionMixin:
    """
    Mixin for views that need to check staff permissions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing request."""
        if not request.user.is_authenticated:
            raise PermissionDenied(_("You must be logged in."))
        
        # Superuser can do anything
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Check if user has staff profile
        if not hasattr(request.user, 'staff_profile'):
            raise PermissionDenied(_("You do not have a staff profile."))
        
        self.staff = request.user.staff_profile
        
        # Check if staff is active
        if not self.staff.is_active:
            raise PermissionDenied(_("Your staff account is inactive."))
        
        return super().dispatch(request, *args, **kwargs)
    
    def check_patient_access(self, patient, request=None):
        """
        Check if current staff can access this patient.
        If request is provided, use it; otherwise use stored staff.
        """
        if hasattr(self, 'staff'):
            return self.staff.can_view_patient(patient)
        elif request and hasattr(request.user, 'staff_profile'):
            return request.user.staff_profile.can_view_patient(patient)
        elif request and request.user.is_superuser:
            return True
        return False
    
    def get_visible_patients(self, request=None):
        """
        Get queryset of patients visible to current staff.
        """
        if hasattr(self, 'staff'):
            return self.staff.get_visible_patients()
        elif request and hasattr(request.user, 'staff_profile'):
            return request.user.staff_profile.get_visible_patients()
        elif request and request.user.is_superuser:
            return Patient.objects.all()
        return Patient.objects.none()