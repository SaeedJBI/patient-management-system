import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import MedicalFile
from patients.models import Patient


@login_required
@staff_member_required
@require_GET
def serve_file(request, file_id):
    """
    Unified view to serve private files.
    Automatically determines whether to preview or download based on:
    - URL path (preview/ vs download/)
    - File type (previewable or not)
    """
    # Get the file
    file_obj = get_object_or_404(MedicalFile, id=file_id, is_active=True)
    
    # Permission check
    if not request.user.is_superuser:
        if hasattr(request.user, 'staff_profile'):
            user_branch = request.user.staff_profile.branch
            if file_obj.patient.branch != user_branch:
                raise PermissionDenied(_("You don't have permission to access this file."))
        else:
            raise PermissionDenied(_("You don't have permission to access this file."))
    
    # Increment download count
    file_obj.increment_download_count()
    
    # Determine if this is a preview request
    is_preview = 'preview' in request.path
    
    # Map file extensions to proper content types with encoding for text files
    content_type_map = {
        'txt': 'text/plain; charset=utf-8',
        'csv': 'text/csv; charset=utf-8',
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'tiff': 'image/tiff',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    
    # Get content type from map or use a safe default
    content_type = content_type_map.get(file_obj.file_extension.lower(), 'application/octet-stream')
    
    # Serve the file
    try:
        # Open the file and create response
        file_content = file_obj.file.open()
        response = FileResponse(file_content, content_type=content_type)
        
        if is_preview and file_obj.can_preview:
            # For preview requests of previewable files, show inline
            response['Content-Disposition'] = f'inline; filename="{file_obj.original_filename}"'
        else:
            # For download requests or non-previewable files, force download
            response['Content-Disposition'] = f'attachment; filename="{file_obj.original_filename}"'
        
        return response
    except FileNotFoundError:
        raise Http404(_("File not found."))
    except Exception as e:
        raise Http404(_("Error accessing file."))


@login_required
def file_upload(request):
    """
    Handle file upload from staff interface.
    """
    if request.method != 'POST':
        messages.error(request, _("Invalid request method."))
        return redirect('staff:patient_search')
    
    # Get form data
    patient_id = request.POST.get('patient_id')
    category = request.POST.get('category')
    title = request.POST.get('title')
    description = request.POST.get('description', '')
    uploaded_file = request.FILES.get('file')
    
    # Validate required fields
    if not all([patient_id, category, title, uploaded_file]):
        messages.error(request, _("All fields are required."))
        return redirect(request.META.get('HTTP_REFERER', 'staff:patient_search'))
    
    # Get patient
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, _("Patient not found."))
        return redirect('staff:patient_search')
    
    # Check permissions
    if not request.user.is_superuser:
        if not hasattr(request.user, 'staff_profile'):
            messages.error(request, _("You don't have permission to upload files."))
            return redirect('staff:patient_search')
        
        staff = request.user.staff_profile
        
        # Check if staff is active
        if not staff.is_active:
            messages.error(request, _("Your staff account is inactive."))
            return redirect('staff:dashboard')
        
        # Check if can view patient
        if not staff.can_view_patient(patient):
            messages.error(request, _("You don't have permission to upload files for this patient."))
            return redirect('staff:patient_detail', patient_id=patient.id)
        
        # Check if can upload this category
        if not staff.can_upload_category(category):
            messages.error(
                request, 
                _(f"Your role ({staff.get_role_display()}) cannot upload files of type: {category}")
            )
            return redirect('staff:patient_detail', patient_id=patient.id)
    
    # Create file record
    try:
        medical_file = MedicalFile(
            patient=patient,
            category=category,
            title=title,
            description=description,
            uploaded_by=request.user,
        )
        
        # Save the file (this will trigger the model's save method which handles metadata)
        medical_file.file.save(uploaded_file.name, uploaded_file, save=True)
        
        messages.success(
            request, 
            _(f"File '{title}' uploaded successfully for {patient.get_full_name()}.")
        )
        
    except Exception as e:
        messages.error(request, _(f"Error uploading file: {str(e)}"))
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"File upload error: {str(e)}", exc_info=True)
    
    return redirect('staff:patient_detail', patient_id=patient.id)