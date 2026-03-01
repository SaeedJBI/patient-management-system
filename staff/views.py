from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from files.models import MedicalFile
from branches.models import Branch
from staff.models import Staff
from .decorators import role_required
from staff.models import ROLE_CHOICES


@login_required
def dashboard(request):
    """
    Role-based dashboard for staff members.
    """
    user = request.user
    
    # Superuser sees admin dashboard
    if user.is_superuser:
        # Get counts for admin dashboard
        total_patients = Patient.objects.count()
        total_files = MedicalFile.objects.count()
        staff_count = Staff.objects.count()
        branch_count = Branch.objects.count()
        recent_patients = Patient.objects.order_by('-created_at')[:10]
        recent_files = MedicalFile.objects.select_related('patient').order_by('-created_at')[:10]
        
        return render(request, 'staff/admin_dashboard.html', {
            'total_patients': total_patients,
            'total_files': total_files,
            'staff_count': staff_count,
            'branch_count': branch_count,
            'recent_patients': recent_patients,
            'recent_files': recent_files,
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
        
        # Role-specific template mapping
        template_map = {
            'doctor': 'staff/doctor_dashboard.html',
            'pharmacist': 'staff/pharmacist_dashboard.html',
            'nutritionist': 'staff/nutritionist_dashboard.html',
            'receptionist': 'staff/receptionist_dashboard.html',
            'finance': 'staff/finance_dashboard.html',
            'branch_admin': 'staff/branch_admin_dashboard.html',
        }
        
        # Get the intended template for this role
        intended_template = template_map.get(staff.role)
        
        # Check if the template exists before using it
        from django.template.loader import get_template
        from django.template import TemplateDoesNotExist
        
        try:
            # Try to get the template - if it exists, use it
            if intended_template:
                get_template(intended_template)
                template = intended_template
            else:
                # Role not in map, use fallback
                template = 'staff/staff_dashboard.html'
        except TemplateDoesNotExist:
            # Template doesn't exist, use fallback
            template = 'staff/staff_dashboard.html'
        except Exception:
            # Any other error, use fallback
            template = 'staff/staff_dashboard.html'
        
        return render(request, template, context)
    
    # Fallback for users with no staff profile
    return render(request, 'staff/dashboard.html', {
        'error': "You don't have a staff profile. Please contact an administrator."
    })


@login_required
def patient_detail(request, patient_id):
    """
    Patient detail view with files grouped by uploader role and category.
    """
    user = request.user
    
    # Get patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check permission to view patient
    if not user.is_superuser:
        if hasattr(user, 'staff_profile'):
            staff = user.staff_profile
            if not staff.can_view_patient(patient):
                return render(request, '403.html', status=403)
        else:
            return render(request, '403.html', status=403)
    
    # Get files using the staff model's get_visible_files method
    if user.is_superuser:
        # Superusers see all files
        files = MedicalFile.objects.filter(patient=patient)
    elif hasattr(user, 'staff_profile'):
        staff = user.staff_profile
        files = staff.get_visible_files(patient=patient)
    else:
        files = MedicalFile.objects.none()
    
    # Order by most recent first
    files = files.order_by('-created_at')
    
    # Group files by uploader role first, then by category
    files_by_role_and_category = {}
    
    # Define all possible roles
    roles = ['doctor', 'receptionist', 'pharmacist', 'nutritionist', 'finance', 'branch_admin', 'super_admin']
    
    for role in roles:
        # Get files for this role
        if role == 'super_admin':
            role_files = files.filter(uploaded_by__is_superuser=True)
        else:
            role_files = files.filter(uploaded_by__staff_profile__role=role)
        
        if role_files.exists():
            # Group these files by category
            category_dict = {}
            for file in role_files:
                category_display = file.get_category_display()
                if category_display not in category_dict:
                    category_dict[category_display] = []
                category_dict[category_display].append(file)
            
            files_by_role_and_category[role] = category_dict
    
    # Also create the simple role-based querysets for backward compatibility
    files_by_role = {
        'all': files,
        'doctor': files.filter(uploaded_by__staff_profile__role='doctor'),
        'receptionist': files.filter(uploaded_by__staff_profile__role='receptionist'),
        'pharmacist': files.filter(uploaded_by__staff_profile__role='pharmacist'),
        'nutritionist': files.filter(uploaded_by__staff_profile__role='nutritionist'),
        'finance': files.filter(uploaded_by__staff_profile__role='finance'),
        'branch_admin': files.filter(uploaded_by__staff_profile__role='branch_admin'),
        'super_admin': files.filter(uploaded_by__is_superuser=True),
    }
    
    # Group by category for the All Files tab
    files_by_category = {}
    for file in files:
        category_display = file.get_category_display()
        if category_display not in files_by_category:
            files_by_category[category_display] = []
        files_by_category[category_display].append(file)
    
    # Get counts for each role
    role_counts = {role: qs.count() for role, qs in files_by_role.items()}
    
    # Check permissions (existing code)
    can_edit_demographics = False
    if user.is_superuser:
        can_edit_demographics = True
    elif hasattr(user, 'staff_profile'):
        can_edit_demographics = user.staff_profile.can_edit_demographics()
    
    can_modify_created_at = False
    if user.is_superuser:
        can_modify_created_at = True
    elif hasattr(user, 'staff_profile'):
        can_modify_created_at = user.staff_profile.can_modify_created_at()
    
    can_create_patients = False
    if user.is_superuser:
        can_create_patients = True
    elif hasattr(user, 'staff_profile'):
        can_create_patients = user.staff_profile.can_create_patients()
    
    # Get allowed upload categories
    allowed_categories = []
    if hasattr(user, 'staff_profile'):
        staff = user.staff_profile
        for cat_value, cat_display in MedicalFile.CATEGORY_CHOICES:
            if staff.can_upload_category(cat_value):
                allowed_categories.append((cat_value, cat_display))
    elif user.is_superuser:
        allowed_categories = MedicalFile.CATEGORY_CHOICES
    
    # Get user role
    user_role = None
    if hasattr(user, 'staff_profile'):
        user_role = user.staff_profile.role
    elif user.is_superuser:
        user_role = 'super_admin'
    
    context = {
        'patient': patient,
        'files_by_role': files_by_role,
        'files_by_category': files_by_category,
        'files_by_role_and_category': files_by_role_and_category,  # NEW: Nested structure
        'role_counts': role_counts,
        'can_edit_demographics': can_edit_demographics,
        'can_modify_created_at': can_modify_created_at,
        'can_create_patients': can_create_patients,
        'allowed_categories': allowed_categories,
        'total_files': files.count(),
        'user_role': user_role,
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
    List files uploaded by current user with advanced filtering.
    """
    user = request.user
    
    # Superusers see all files, others see their own
    if user.is_superuser:
        files = MedicalFile.objects.select_related('patient', 'uploaded_by', 'patient__branch').order_by('-created_at')
    else:
        files = MedicalFile.objects.filter(uploaded_by=user).select_related('patient', 'uploaded_by', 'patient__branch').order_by('-created_at')
    
    # Get data for filters
    from patients.models import Patient
    from staff.models import Staff, ROLE_CHOICES  # Import ROLE_CHOICES here
    from branches.models import Branch
    
    all_patients = Patient.objects.all().order_by('last_name', 'first_name')
    all_staff = Staff.objects.select_related('user').all().order_by('user__first_name')
    all_branches = Branch.objects.all().order_by('name')
    
    # Role choices for filter
    role_choices = ROLE_CHOICES  # Now this works
    
    # Category choices
    category_choices = MedicalFile.CATEGORY_CHOICES
    
    # Calculate stats
    unique_patients = files.values('patient').distinct().count()
    unique_staff = files.values('uploaded_by').distinct().count()
    total_size = sum(f.file_size or 0 for f in files)
    
    # Format total size
    if total_size < 1024:
        total_size_display = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_size_display = f"{total_size/1024:.1f} KB"
    elif total_size < 1024 * 1024 * 1024:
        total_size_display = f"{total_size/(1024*1024):.1f} MB"
    else:
        total_size_display = f"{total_size/(1024*1024*1024):.1f} GB"
    
    return render(request, 'staff/file_uploads.html', {
        'files': files,
        'all_patients': all_patients,
        'all_staff': all_staff,
        'all_branches': all_branches,
        'role_choices': role_choices,
        'category_choices': category_choices,
        'unique_patients_count': unique_patients,
        'unique_staff_count': unique_staff,
        'total_size': total_size_display,
        'total_files': files.count(),
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


# ===== NEW VIEW ADDED FOR RECEPTIONISTS =====
@login_required
def receptionist_add_patient(request):
    """
    View for receptionists to add new patients with back-dating capability.
    """
    from django.contrib import messages
    from django.utils.translation import gettext as _
    import uuid
    
    # Check if user has permission
    if not request.user.is_superuser:
        if not hasattr(request.user, 'staff_profile') or request.user.staff_profile.role != 'receptionist':
            messages.error(request, _("You don't have permission to add patients."))
            return redirect('staff:dashboard')
    
    if request.method == 'POST':
        # Get receptionist's branch
        if request.user.is_superuser:
            branch = Branch.objects.first()
        else:
            branch = request.user.staff_profile.branch
        
        # Get back-dated created_at if provided
        created_at = request.POST.get('created_at')
        if created_at:
            try:
                from django.utils.dateparse import parse_datetime
                created_at = parse_datetime(created_at)
            except:
                created_at = timezone.now()
        else:
            created_at = timezone.now()
        
        # Create patient with all fields
        try:
            patient = Patient.objects.create(
                # Branch
                branch=branch,
                
                # Personal Information
                first_name=request.POST.get('first_name'),
                middle_name=request.POST.get('middle_name', ''),
                last_name=request.POST.get('last_name'),
                mother_name=request.POST.get('mother_name', ''),
                date_of_birth=request.POST.get('date_of_birth'),
                place_of_birth=request.POST.get('place_of_birth', ''),
                gender=request.POST.get('gender'),
                marital_status=request.POST.get('marital_status', ''),
                nationality=request.POST.get('nationality', 'Jordanian'),
                
                # Identification
                national_id=request.POST.get('national_id'),
                # mrn will be auto-generated
                
                # Contact Information
                phone_mobile=request.POST.get('phone_mobile'),
                phone_home=request.POST.get('phone_home', ''),
                phone_work=request.POST.get('phone_work', ''),
                email=request.POST.get('email', ''),
                
                # Address
                address_line1=request.POST.get('address_line1', ''),
                address_line2=request.POST.get('address_line2', ''),
                city=request.POST.get('city', 'Amman'),
                state=request.POST.get('state', 'Amman'),
                postal_code=request.POST.get('postal_code', ''),
                country=request.POST.get('country', 'Jordan'),
                
                # Emergency Contact
                emergency_contact_name=request.POST.get('emergency_contact_name', ''),
                emergency_contact_relationship=request.POST.get('emergency_contact_relationship', ''),
                emergency_contact_phone=request.POST.get('emergency_contact_phone', ''),
                
                # Insurance
                insurance_provider=request.POST.get('insurance_provider', ''),
                insurance_policy_number=request.POST.get('insurance_policy_number', ''),
                insurance_expiry_date=request.POST.get('insurance_expiry_date') or None,
                
                # Medical Flags
                has_allergies=request.POST.get('has_allergies') == 'on',
                allergy_notes=request.POST.get('allergy_notes', ''),
                has_chronic_conditions=request.POST.get('has_chronic_conditions') == 'on',
                chronic_conditions_notes=request.POST.get('chronic_conditions_notes', ''),
                blood_type=request.POST.get('blood_type', 'unknown'),
                
                # Notes
                notes=request.POST.get('notes', ''),
                
                # Audit
                created_by=request.user,
                updated_by=request.user,
            )
            
            # Override created_at if back-dated
            if created_at:
                patient.created_at = created_at
                patient.save(update_fields=['created_at'])
            
            messages.success(request, _(f"Patient {patient.get_full_name()} created successfully."))
            return redirect('staff:patient_detail', patient_id=patient.id)
            
        except Exception as e:
            messages.error(request, _(f"Error creating patient: {str(e)}"))
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Patient creation error: {str(e)}", exc_info=True)
    
    # GET request - show form
    return render(request, 'staff/receptionist_add_patient.html', {
        'today': timezone.now().date(),
    })