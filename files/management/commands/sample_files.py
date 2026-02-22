import os
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from patients.models import Patient
from core.models import User
from files.models import MedicalFile


class Command(BaseCommand):
    help = 'Create sample medical files for testing'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5, help='Number of files per patient')

    def handle(self, *args, **options):
        count = options['count']
        
        # Get patients
        patients = Patient.objects.all()
        if not patients:
            self.stdout.write(self.style.ERROR('No patients found. Run sample_patients first.'))
            return
        
        # Get user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No superuser found.'))
            return
        
        categories = [c[0] for c in MedicalFile.CATEGORY_CHOICES]
        
        for patient in patients:
            for i in range(count):
                # Create a dummy file content
                file_content = f"Sample medical file for {patient.get_full_name()} - File {i+1}\n"
                file_content += f"Patient MRN: {patient.mrn}\n"
                file_content += f"Date: {patient.created_at}\n"
                file_content += f"This is a test file for the PMS system."
                
                file_name = f"sample_{i+1}.txt"
                
                # Choose random category
                category = random.choice(categories)
                
                # Create file
                medical_file = MedicalFile(
                    patient=patient,
                    category=category,
                    title=f"{category.replace('_', ' ').title()} - Sample {i+1}",
                    description=f"Sample {category} file for testing",
                    uploaded_by=user,
                )
                
                # Save file - this will trigger the updated save() method
                medical_file.file.save(
                    file_name,
                    ContentFile(file_content.encode('utf-8')),
                    save=True
                )
                
                self.stdout.write(f"Created file: {medical_file.title} for {patient.get_full_name()} (Size: {medical_file.file_size_display})")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created sample files for {patients.count()} patients'))