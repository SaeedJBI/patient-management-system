from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation import check_for_language, activate
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import translate_url


def set_language(request):
    """
    Custom language switching view that preserves the current page.
    """
    if request.method == 'POST':
        lang_code = request.POST.get('language')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        
        if lang_code and check_for_language(lang_code):
            # Ensure the next URL is safe
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                # Activate the language
                activate(lang_code)
                
                # Store in session
                if hasattr(request, 'session'):
                    request.session['django_language'] = lang_code
                
                # Update user preference if authenticated
                if hasattr(request, 'user') and request.user.is_authenticated:
                    if request.user.language != lang_code:
                        request.user.language = lang_code
                        request.user.save(update_fields=['language'])
                
                # Create response with cookie
                response = HttpResponseRedirect(next_url)
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    lang_code,
                    max_age=365 * 24 * 60 * 60,  # 1 year
                    httponly=True,
                    samesite='Lax',
                )
                
                # Also set a flag to ensure middleware picks it up
                response.set_cookie('language_just_changed', '1', max_age=5)
                
                return response
    
    # Fallback
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def login_redirect(request):
    """Redirect users based on their role after login."""
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin:index')
        return redirect('staff_dashboard')
    return redirect('admin:login')