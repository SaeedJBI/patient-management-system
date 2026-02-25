from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from branches.models import Branch
from staff.models import Staff, ROLE_CHOICES

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a staff member'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='User email')
        parser.add_argument('--first-name', required=True, help='First name')
        parser.add_argument('--last-name', required=True, help='Last name')
        parser.add_argument('--role', required=True, choices=[r[0] for r in ROLE_CHOICES])
        parser.add_argument('--branch-code', required=True, help='Branch code')
        parser.add_argument('--employee-id', required=True, help='Employee ID')
        parser.add_argument('--password', default='changeme123', help='Password')

    def handle(self, *args, **options):
        # Get branch
        try:
            branch = Branch.objects.get(code=options['branch_code'])
        except Branch.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Branch not found: {options['branch_code']}"))
            return
        
        # Create or get user
        user, created = User.objects.get_or_create(
            email=options['email'],
            defaults={
                'first_name': options['first_name'],
                'last_name': options['last_name'],
                'is_staff': True,
            }
        )
        
        if created:
            user.set_password(options['password'])
            user.save()
            self.stdout.write(f"Created user: {user.email}")
        else:
            self.stdout.write(f"Using existing user: {user.email}")
        
        # Create staff profile
        staff, created = Staff.objects.get_or_create(
            user=user,
            defaults={
                'branch': branch,
                'role': options['role'],
                'employee_id': options['employee_id'],
                'joined_date': timezone.now().date(),
                'created_by': user,  # Self-created during setup
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created staff: {user.get_full_name()} as {options['role']} at {branch.code}"
            ))
        else:
            self.stdout.write(self.style.WARNING(f"Staff profile already exists for {user.email}"))