from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from files.models import MedicalFile
from .decorators import role_required


@login_required
def dashboard(request):
    """
    Role-based dashboard for staff members.
    """
    user = request.user
    
    # Superuser sees admin dashboard
    if user.is_superuser:
        return render(request, 'staff/admin_dashboard.html', {
            'total_patients': Patient.objects.count(),
            'total_files': MedicalFile.objects.count(),
            'recent_patients': Patient.objects.order_by('-created_at')[:10],
            'recent_files': MedicalFile.objects.select_related('patient').order_by('-created_at')[:10],
        })
    
    # Staff member dashboard
    if hasattr(user, 'staff_profile'):
        staff = user.staff_profile
        
        # Get patients visible to this staff member
        patients = staff.get_visible_patients()
        
        # Get recent files from these patients
        recent_files = MedicalFile.objects.filter(
            patient__in=patients
        ).select_related('patient').order_by('-created_at')[:20]
        
        # Get counts by category for quick access
        file_categories = MedicalFile.objects.filter(
            patient__in=patients
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Get patients with recent activity
        recent_patients = patients.order_by('-updated_at')[:10]
        
        # Role-specific context
        context = {
            'staff': staff,
            'patients_count': patients.count(),
            'files_count': recent_files.count(),
            'recent_files': recent_files,
            'recent_patients': recent_patients,
            'file_categories': file_categories,
        }
        
        # Role-specific template
        template_map = {
            'doctor': 'staff/doctor_dashboard.html',
            'pharmacist': 'staff/pharmacist_dashboard.html',
            'nutritionist': 'staff/nutritionist_dashboard.html',
            'receptionist': 'staff/receptionist_dashboard.html',
            'branch_admin': 'staff/branch_admin_dashboard.html',
        }
        
        template = template_map.get(staff.role, 'staff/staff_dashboard.html')
        return render(request, template, context)
    
    # Fallback
    return render(request, 'staff/dashboard.html')


@login_required
def patient_detail(request, patient_id):
    """
    Patient detail view with files grouped by category.
    """
    user = request.user
    
    # Get patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check permission
    if not user.is_superuser:
        if hasattr(user, 'staff_profile'):
            staff = user.staff_profile
            if not staff.can_view_patient(patient):
                return render(request, '403.html', status=403)
        else:
            return render(request, '403.html', status=403)
    
    # Get files grouped by category
    files = MedicalFile.objects.filter(patient=patient).order_by('-created_at')
    
    files_by_category = {}
    for category_display, category_value in MedicalFile.CATEGORY_CHOICES:
        category_files = files.filter(category=category_value)
        if category_files.exists():
            files_by_category[category_display] = category_files[:10]
    
    # Check if user can edit demographics
    can_edit_demographics = False
    if user.is_superuser:
        can_edit_demographics = True
    elif hasattr(user, 'staff_profile'):
        can_edit_demographics = user.staff_profile.can_edit_demographics()
    
    # Get allowed upload categories for this user
    allowed_categories = []
    if hasattr(user, 'staff_profile'):
        staff = user.staff_profile
        for cat_value, cat_display in MedicalFile.CATEGORY_CHOICES:
            if staff.can_upload_category(cat_value):
                allowed_categories.append((cat_value, cat_display))
    
    context = {
        'patient': patient,
        'files_by_category': files_by_category,
        'can_edit_demographics': can_edit_demographics,
        'allowed_categories': allowed_categories,
        'total_files': files.count(),
    }
    
    return render(request, 'staff/patient_detail.html', context)


@login_required
def patient_search(request):
    """
    Search page for patients.
    """
    return render(request, 'staff/patient_search.html')


@login_required
def recent_patients(request):
    """
    List recently viewed/updated patients.
    """
    user = request.user
    
    if user.is_superuser:
        patients = Patient.objects.order_by('-updated_at')[:50]
    elif hasattr(user, 'staff_profile'):
        staff = user.staff_profile
        patients = staff.get_visible_patients().order_by('-updated_at')[:50]
    else:
        patients = []
    
    return render(request, 'staff/recent_patients.html', {
        'patients': patients
    })


@login_required
def file_uploads(request):
    """
    List files uploaded by current user.
    """
    user = request.user
    
    files = MedicalFile.objects.filter(uploaded_by=user).select_related('patient').order_by('-created_at')
    
    return render(request, 'staff/file_uploads.html', {
        'files': files
    })


@login_required
def staff_profile(request):
    """
    Staff profile view.
    """
    user = request.user
    
    context = {
        'user': user,
    }
    
    if hasattr(user, 'staff_profile'):
        context['staff'] = user.staff_profile
        context['patients_count'] = user.staff_profile.assigned_patients.count()
        context['files_count'] = MedicalFile.objects.filter(uploaded_by=user).count()
    
    return render(request, 'staff/profile.html', context)