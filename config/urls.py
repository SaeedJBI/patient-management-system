"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse

# Force admin registration to be loaded
import core.admin
import branches.admin

# Helper function to redirect root to language-prefixed admin
def redirect_to_admin(request):
    """Redirect root URL to language-prefixed admin interface."""
    lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, 'en')
    valid_languages = ['en', 'ar']
    if lang not in valid_languages:
        lang = 'en'
    return redirect(f'/{lang}/admin/')

# Base URLs without language prefix
urlpatterns = [
    path('', redirect_to_admin, name='root-redirect'),
    path('i18n/', include('django.conf.urls.i18n')),
]

# English URLs
urlpatterns += [
    path('en/', include([
        path('admin/', admin.site.urls),
        path('core/', include(('core.urls', 'core'), namespace='en_core')),
    ])),
]

# Arabic URLs
urlpatterns += [
    path('ar/', include([
        path('admin/', admin.site.urls),
        path('core/', include(('core.urls', 'core'), namespace='ar_core')),
    ])),
]

# Serve media and static files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug view
if settings.DEBUG:
    def list_urls(request):
        from django.urls import get_resolver
        resolver = get_resolver()
        url_list = []
        for pattern in resolver.url_patterns:
            url_list.append(str(pattern))
        return HttpResponse('<br>'.join(url_list))
    
    urlpatterns.append(path('debug-urls/', list_urls, name='debug-urls'))