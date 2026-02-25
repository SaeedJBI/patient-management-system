import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from .models import MedicalFile
from django.utils.translation import gettext_lazy as _ 


@login_required
@staff_member_required
@require_GET
def serve_private_file(request, file_id):
    """
    Securely serve private files to authenticated staff members.
    This view checks permissions before serving the file.
    """
    # Get the file
    file_obj = get_object_or_404(MedicalFile, id=file_id, is_active=True)
    
    # Permission check: Staff can only access files from their branch
    if not request.user.is_superuser:
        # Superusers can access all files
        # Regular staff can only access files from their branch
        if hasattr(request.user, 'staff_profile'):
            user_branch = request.user.staff_profile.branch
            if file_obj.patient.branch != user_branch:
                raise PermissionDenied(_("You don't have permission to access this file."))
    
    # Increment download count
    file_obj.increment_download_count()
    
    # Serve the file
    try:
        response = FileResponse(file_obj.file, as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{file_obj.original_filename}"'
        return response
    except FileNotFoundError:
        raise Http404(_("File not found."))