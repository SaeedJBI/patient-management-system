from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation import check_for_language, activate
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import translate_url  # This is important!


def set_language(request):
    """
    Custom language switching view that preserves the current page
    AND translates the URL to the new language.
    """
    if request.method == 'POST':
        lang_code = request.POST.get('language')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        
        if lang_code and check_for_language(lang_code):
            # Ensure the next URL is safe
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                # TRANSLATE THE URL to the new language (e.g., /en/staff/ -> /ar/staff/)
                next_url = translate_url(next_url, lang_code)
                
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
                
                # Create response with cookie and redirect to translated URL
                response = HttpResponseRedirect(next_url)
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    lang_code,
                    max_age=365 * 24 * 60 * 60,  # 1 year
                    httponly=True,
                    samesite='Lax',
                )
                
                return response
    
    # Fallback
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def login_redirect(request):
    """Redirect users based on their role after login."""
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin:index')
        return redirect('staff:dashboard')
    return redirect('admin:login')

# for production setup
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth import get_user_model
from io import StringIO
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def setup_view(request):
    """Temporary public endpoint to initialize the database on Render."""
    output = StringIO()
    
    output.write("="*50 + "\n")
    output.write("PMS SETUP SCRIPT\n")
    output.write("="*50 + "\n\n")
    
    # Run migrations
    output.write("Running migrations...\n")
    call_command('migrate', stdout=output, interactive=False)
    output.write("✓ Migrations complete\n\n")
    
    # Create superuser if doesn't exist
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        output.write("Creating superuser...\n")
        User.objects.create_superuser(
            email='admin@pms.local',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        output.write("✓ Superuser created\n")
        output.write("  Email: admin@pms.local\n")
        output.write("  Password: admin123\n\n")
    else:
        output.write("✓ Superuser already exists\n\n")
    
    # Create a default branch if none exists
    from branches.models import Branch
    from django.utils import timezone
    
    if not Branch.objects.exists():
        output.write("Creating default branch...\n")
        admin = User.objects.get(email='admin@pms.local')
        branch = Branch.objects.create(
            name='Main Branch',
            code='MAIN',
            address='123 Healthcare Street',
            city='Amman',
            state='Amman',
            postal_code='11110',
            country='Jordan',
            phone='+962-6-500-0000',
            email='main@hospital.jo',
            opened_date=timezone.now().date(),
            created_by=admin,
            is_active=True
        )
        output.write(f"✓ Branch created: {branch.name} ({branch.code})\n\n")
    else:
        output.write("✓ Branch already exists\n\n")
    
    output.write("="*50 + "\n")
    output.write("SETUP COMPLETE\n")
    output.write("="*50 + "\n")
    output.write("\nYou can now log in with:\n")
    output.write("- Email: admin@pms.local\n")
    output.write("- Password: admin123\n")
    
    return HttpResponse(f"<pre>{output.getvalue()}</pre>")