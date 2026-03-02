from django.db import models
from django.db.models import Q, F, Value
from django.db.models.functions import Concat
from django.contrib.postgres.search import TrigramSimilarity
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from files.models import MedicalFile
from .models import RecentSearch


class PatientSearchManager:
    """
    Manager class for searching patients with permission filtering.
    Uses PostgreSQL trigram similarity for fuzzy matching.
    """
    
    def __init__(self, user):
        self.user = user
        self.staff = getattr(user, 'staff_profile', None)
    
    def get_visible_patients_queryset(self):
        """
        Get base queryset of patients visible to current user.
        """
        if self.user.is_superuser:
            return Patient.objects.all()
        
        if not self.staff:
            return Patient.objects.none()
        
        if self.staff.role == 'branch_admin':
            return Patient.objects.filter(branch=self.staff.branch)
        
        # Doctor, receptionist, finance see all patients in branch
        if self.staff.role in ['doctor', 'receptionist', 'finance']:
            return Patient.objects.filter(branch=self.staff.branch)
        
        return self.staff.assigned_patients.all()
    
    def search(self, query, filters=None, page=1, page_size=20):
        """
        Perform search with fuzzy matching.
        If query is empty, return all visible patients (with filters applied).
        """
        filters = filters or {}
        
        # Get visible patients
        base_qs = self.get_visible_patients_queryset()
        
        # NEW: Handle empty query - return all visible patients
        if not query or len(query.strip()) == 0:
            # Apply filters
            results = base_qs
            
            if filters.get('branch'):
                results = results.filter(branch_id=filters['branch'])
            
            if filters.get('gender'):
                results = results.filter(gender=filters['gender'])
            
            if filters.get('age_min'):
                max_date = timezone.now().date() - timedelta(days=int(filters['age_min'])*365)
                results = results.filter(date_of_birth__lte=max_date)
            
            if filters.get('age_max'):
                min_date = timezone.now().date() - timedelta(days=int(filters['age_max'])*365)
                results = results.filter(date_of_birth__gte=min_date)
            
            # Order by name
            results = results.order_by('last_name', 'first_name')
            
            # Paginate
            total = results.count()
            start = (page - 1) * page_size
            end = start + page_size
            paginated_results = results[start:end]
            
            return {
                'results': paginated_results,
                'total': total,
                'page': page,
                'page_size': page_size,
                'query': query,
                'filters': filters
            }
        
        # Return empty if query too short (less than 2 chars)
        if len(query.strip()) < 2:
            return {
                'results': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'query': query
            }
        
        query = query.strip()
        
        # STEP 1: Exact matches (highest priority)
        exact_match_qs = base_qs.filter(
            Q(mrn__iexact=query) |
            Q(national_id__iexact=query) |
            Q(email__iexact=query) |
            Q(phone_mobile__iexact=query)
        )
        
        if exact_match_qs.exists():
            results = exact_match_qs
            total = results.count()
            start = (page - 1) * page_size
            end = start + page_size
            
            return {
                'results': results[start:end],
                'total': total,
                'page': page,
                'page_size': page_size,
                'query': query,
                'filters': filters
            }
        
        # STEP 2: Fuzzy matching on names
        # Create full name for better matching
        base_qs = base_qs.annotate(
            full_name=Concat(
                F('first_name'), Value(' '),
                F('middle_name'), Value(' '),
                F('last_name')
            )
        )
        
        # Calculate similarity scores
        results = base_qs.annotate(
            first_sim=TrigramSimilarity('first_name', query),
            last_sim=TrigramSimilarity('last_name', query),
            full_sim=TrigramSimilarity('full_name', query)
        ).filter(
            # Similarity threshold > 0.2
            Q(first_sim__gt=0.2) |
            Q(last_sim__gt=0.2) |
            Q(full_sim__gt=0.2) |
            # Fallback to partial matching
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(middle_name__icontains=query) |
            Q(mrn__icontains=query) |
            Q(national_id__icontains=query) |
            Q(phone_mobile__icontains=query) |
            Q(email__icontains=query)
        ).annotate(
            total_sim=F('first_sim') + F('last_sim') + F('full_sim')
        ).order_by('-total_sim', 'last_name', 'first_name')
        
        # Apply filters
        if filters.get('branch'):
            results = results.filter(branch_id=filters['branch'])
        
        if filters.get('gender'):
            results = results.filter(gender=filters['gender'])
        
        if filters.get('age_min'):
            max_date = timezone.now().date() - timedelta(days=int(filters['age_min'])*365)
            results = results.filter(date_of_birth__lte=max_date)
        
        if filters.get('age_max'):
            min_date = timezone.now().date() - timedelta(days=int(filters['age_max'])*365)
            results = results.filter(date_of_birth__gte=min_date)
        
        # Paginate
        total = results.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        # Track search
        if query and len(query) >= 3:
            RecentSearch.objects.create(
                user=self.user,
                query=query,
                filters=filters,
                result_count=total
            )
        
        return {
            'results': paginated_results,
            'total': total,
            'page': page,
            'page_size': page_size,
            'query': query,
            'filters': filters
        }
    
    def search_files(self, query, patient_id=None, page=1, page_size=20):
        """
        Search within medical files.
        """
        visible_patients = self.get_visible_patients_queryset()
        files = MedicalFile.objects.filter(patient__in=visible_patients)
        
        if patient_id:
            files = files.filter(patient_id=patient_id)
        
        if query and len(query) >= 2:
            files = files.annotate(
                title_sim=TrigramSimilarity('title', query),
                filename_sim=TrigramSimilarity('original_filename', query)
            ).filter(
                Q(title_sim__gt=0.3) |
                Q(filename_sim__gt=0.3) |
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(original_filename__icontains=query) |
                Q(category__icontains=query)
            ).annotate(
                total_sim=F('title_sim') + F('filename_sim')
            ).order_by('-total_sim', '-created_at')
        else:
            files = files.order_by('-created_at')
        
        total = files.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        return {
            'results': files[start:end],
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def suggest(self, partial, limit=5):
        """
        Provide search suggestions.
        """
        if len(partial) < 2:
            return []
        
        visible_patients = self.get_visible_patients_queryset()
        
        suggestions = visible_patients.annotate(
            first_sim=TrigramSimilarity('first_name', partial),
            last_sim=TrigramSimilarity('last_name', partial)
        ).filter(
            Q(first_sim__gt=0.2) |
            Q(last_sim__gt=0.2) |
            Q(first_name__icontains=partial) |
            Q(last_name__icontains=partial) |
            Q(mrn__icontains=partial) |
            Q(national_id__icontains=partial)
        ).annotate(
            best_sim=F('first_sim') + F('last_sim')
        ).order_by('-best_sim').values(
            'id', 'first_name', 'last_name', 'mrn'
        )[:limit]
        
        return list(suggestions)