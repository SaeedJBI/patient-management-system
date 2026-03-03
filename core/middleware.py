from django.utils import translation
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class UserLanguageMiddleware:
    """
    Middleware to set language based on authenticated user's preference.
    Must run AFTER AuthenticationMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Determine language: cookie > session > user preference > default
        lang = None
        
        # Check cookie first
        if settings.LANGUAGE_COOKIE_NAME in request.COOKIES:
            lang = request.COOKIES[settings.LANGUAGE_COOKIE_NAME]
        
        # Then check session
        if not lang and hasattr(request, 'session') and 'django_language' in request.session:
            lang = request.session['django_language']
        
        # Then check authenticated user
        if not lang and hasattr(request, 'user') and request.user.is_authenticated:
            user_lang = getattr(request.user, 'language', None)
            if user_lang and user_lang in [code for code, _ in settings.LANGUAGES]:
                lang = user_lang
        
        # Validate and activate
        valid_languages = [code for code, _ in settings.LANGUAGES]
        if lang and lang in valid_languages:
            translation.activate(lang)
            # Ensure it's in the session
            if hasattr(request, 'session'):
                request.session['django_language'] = lang
        
        # Process the view
        response = self.get_response(request)
        
        # If user is authenticated, ensure cookie is set
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_lang = getattr(request.user, 'language', None)
            if user_lang and user_lang in valid_languages:
                # Set cookie if not already set or different
                current_cookie = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
                if current_cookie != user_lang:
                    response.set_cookie(
                        settings.LANGUAGE_COOKIE_NAME,
                        user_lang,
                        max_age=365 * 24 * 60 * 60,  # 1 year
                        httponly=True,
                        samesite='Lax',
                    )
        
        return response
    
class StaffAdminRedirectMiddleware:
    """
    Middleware to redirect staff users away from admin to staff dashboard.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if user is authenticated, is staff but NOT superuser
        if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser:
            # If they're trying to access any admin page
            if request.path.startswith('/en/admin/') or request.path.startswith('/ar/admin/'):
                # Redirect them to staff dashboard
                lang = 'en' if request.path.startswith('/en/') else 'ar'
                return redirect(f'/{lang}/staff/')
        
        return response