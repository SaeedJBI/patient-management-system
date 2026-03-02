from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .managers import PatientSearchManager
from django.utils import timezone 


@login_required
@require_GET
def search_api(request):
    """
    JSON API endpoint for search.
    """
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    # Parse filters
    filters = {}
    if request.GET.get('branch'):
        filters['branch'] = request.GET.get('branch')
    if request.GET.get('gender'):
        filters['gender'] = request.GET.get('gender')
    if request.GET.get('age_min'):
        filters['age_min'] = int(request.GET.get('age_min'))
    if request.GET.get('age_max'):
        filters['age_max'] = int(request.GET.get('age_max'))
    
    # Perform search
    search_manager = PatientSearchManager(request.user)
    results = search_manager.search(query, filters, page, page_size)
    
    # Format for JSON
    data = {
        'results': [
            {
                'id': str(p.id),
                'mrn': p.mrn,
                'name': p.get_full_name(),
                'national_id': p.national_id,
                'gender': p.get_gender_display(),
                'age': p.get_age(),
                'phone': p.phone_mobile,
                'branch': p.branch.code if p.branch else '',
            }
            for p in results['results']
        ],
        'total': results['total'],
        'page': results['page'],
        'page_size': results['page_size'],
        'query': results['query'],
    }
    
    return JsonResponse(data)


@login_required
def search_suggestions(request):
    """
    API endpoint for type-ahead suggestions.
    """
    partial = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 5))
    
    search_manager = PatientSearchManager(request.user)
    suggestions = search_manager.suggest(partial, limit)
    
    return JsonResponse({'suggestions': suggestions})

@login_required
@require_GET
def show_all_api(request):
    """
    API endpoint for showing all patients (with filters).
    More efficient than using empty query search.
    """
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    # Parse filters
    filters = {}
    if request.GET.get('branch'):
        filters['branch'] = request.GET.get('branch')
    if request.GET.get('gender'):
        filters['gender'] = request.GET.get('gender')
    if request.GET.get('age_min'):
        filters['age_min'] = int(request.GET.get('age_min'))
    if request.GET.get('age_max'):
        filters['age_max'] = int(request.GET.get('age_max'))
    
    # Get visible patients
    search_manager = PatientSearchManager(request.user)
    base_qs = search_manager.get_visible_patients_queryset()
    
    # Apply filters
    results = base_qs
    
    if filters.get('branch'):
        results = results.filter(branch_id=filters['branch'])
    
    if filters.get('gender'):
        results = results.filter(gender=filters['gender'])
    
    if filters.get('age_min'):
        from datetime import timedelta
        max_date = timezone.now().date() - timedelta(days=filters['age_min']*365)
        results = results.filter(date_of_birth__lte=max_date)
    
    if filters.get('age_max'):
        from datetime import timedelta
        min_date = timezone.now().date() - timedelta(days=filters['age_max']*365)
        results = results.filter(date_of_birth__gte=min_date)
    
    # Order by name
    results = results.order_by('last_name', 'first_name')
    
    # Paginate
    total = results.count()
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = results[start:end]
    
    # Format response
    data = {
        'results': [
            {
                'id': str(p.id),
                'mrn': p.mrn,
                'name': p.get_full_name(),
                'national_id': p.national_id,
                'gender': p.get_gender_display(),
                'age': p.get_age(),
                'phone': p.phone_mobile,
                'branch': p.branch.code,
            }
            for p in paginated_results
        ],
        'total': total,
        'page': page,
        'page_size': page_size,
    }
    
    return JsonResponse(data)

@login_required
def search_page(request):
    """
    Render the search interface.
    """
    return render(request, 'search/search.html')