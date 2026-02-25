from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def role_required(allowed_roles):
    """
    Decorator to restrict access based on staff role.
    
    Usage:
        @role_required(['doctor', 'branch_admin'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Superuser can access everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if user has staff profile
            if not hasattr(request.user, 'staff_profile'):
                messages.error(request, "You don't have a staff profile.")
                return redirect('staff_dashboard')
            
            # Check if role is allowed
            staff = request.user.staff_profile
            if staff.role in allowed_roles or 'all' in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # Not authorized
            messages.error(request, "You don't have permission to access this page.")
            raise PermissionDenied
        
        return _wrapped_view
    
    return decorator


def patient_access_required(view_func):
    """
    Decorator to ensure user has access to the patient.
    Assumes patient_id is in kwargs.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from patients.models import Patient
        
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            return view_func(request, *args, **kwargs)
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, "Patient not found.")
            return redirect('patient_search')
        
        # Check permission
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if hasattr(request.user, 'staff_profile'):
            staff = request.user.staff_profile
            if staff.can_view_patient(patient):
                return view_func(request, *args, **kwargs)
        
        messages.error(request, "You don't have access to this patient.")
        raise PermissionDenied
    
    return _wrapped_view