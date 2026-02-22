from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random
from branches.models import Branch
from core.models import User
from patients.models import Patient


class Command(BaseCommand):
    help = 'Create sample patients for testing'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Number of patients to create')

    def handle(self, *args, **options):
        count = options['count']
        
        # Get first branch and user
        branch = Branch.objects.first()
        if not branch:
            self.stdout.write(self.style.ERROR('No branches found. Run init_pms first.'))
            return
        
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No superuser found. Run init_pms first.'))
            return
        
        first_names = ['Ahmed', 'Mohammed', 'Fatima', 'Omar', 'Layla', 'Yousef', 'Mariam', 'Ali', 'Khadija', 'Hassan']
        last_names = ['Hassan', 'Mohammed', 'Ali', 'Ahmed', 'Saleh', 'Abdullah', 'Hussein', 'Karim', 'Said', 'Nasser']
        
        for i in range(count):
            # Generate random date of birth (between 1 and 80 years ago)
            days_ago = random.randint(365, 80*365)
            dob = date.today() - timedelta(days=days_ago)
            
            gender = random.choice(['M', 'F'])
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            patient = Patient.objects.create(
                branch=branch,
                national_id=f"{random.randint(1000000000, 9999999999)}",
                first_name=first_name,
                last_name=last_name,
                mother_name=f"Mother of {first_name}",
                date_of_birth=dob,
                gender=gender,
                nationality='Jordanian',
                phone_mobile=f"079{random.randint(1000000, 9999999)}",
                address_line1=f"Street {random.randint(1, 100)}",
                city='Amman',
                state='Amman',
                country='Jordan',
                emergency_contact_name=f"Emergency Contact {i}",
                emergency_contact_relationship='Family',
                emergency_contact_phone=f"078{random.randint(1000000, 9999999)}",
                created_by=user,
                updated_by=user,
            )
            
            self.stdout.write(f"Created patient: {patient.get_full_name()} ({patient.mrn})")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} sample patients'))