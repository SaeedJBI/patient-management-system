from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Branch


@staff_member_required
def branch_list_api(request):
    """API endpoint to get list of branches for filters."""
    branches = Branch.objects.filter(is_active=True).values('id', 'name', 'code')
    return JsonResponse(list(branches), safe=False)