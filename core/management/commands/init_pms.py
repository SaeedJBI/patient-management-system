from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from branches.models import Branch
from django.utils import timezone
from datetime import datetime

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize PMS with default admin user and branch'

    def handle(self, *args, **options):
        self.stdout.write('Initializing PMS...')
        
        # Create default branch if none exists
        if not Branch.objects.exists():
            branch = Branch.objects.create(
                name='Main Branch',
                code='MAIN',
                address='123 Main Street',
                city='New York',
                state='NY',
                postal_code='10001',
                country='USA',
                phone='+1-212-555-1234',
                email='main@example.com',
                opened_date=timezone.now().date(),
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created branch: {branch}'))
        else:
            branch = Branch.objects.first()
            self.stdout.write(f'Using existing branch: {branch}')
        
        # Create superuser if none exists
        if not User.objects.filter(is_superuser=True).exists():
            admin = User.objects.create_superuser(
                email='admin@pms.local',
                password='admin123',
                first_name='Admin',
                last_name='User',
                employee_id='ADMIN001',
                is_staff=True,
                is_active=True,
                language='en'  # Set default language
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin.email}'))
            
            local_created = timezone.localtime(admin.date_joined)
            self.stdout.write(f"Account created at: {local_created.strftime('%b. %d, %Y, %I:%M %p')}")
            self.stdout.write(f"Default language set to: {admin.get_language_display()}")
        else:
            self.stdout.write('Admin user already exists')
            # Update existing admin to have language if not set
            admin = User.objects.filter(is_superuser=True).first()
            if admin and not admin.language:
                admin.language = 'en'
                admin.save()
                self.stdout.write(f"Updated {admin.email} with default language")
        
        self.stdout.write(self.style.SUCCESS('PMS initialization complete!'))