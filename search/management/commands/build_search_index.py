from django.core.management.base import BaseCommand
from patients.models import Patient
from search.models import PatientSearchIndex
from django.db import transaction


class Command(BaseCommand):
    help = 'Build search index for all patients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Delete existing index and rebuild from scratch',
        )

    def handle(self, *args, **options):
        self.stdout.write('Building search index...')
        
        if options['rebuild']:
            self.stdout.write('Deleting existing index...')
            PatientSearchIndex.objects.all().delete()
        
        count = 0
        error_count = 0
        total_patients = Patient.objects.count()
        
        self.stdout.write(f'Found {total_patients} patients to index')
        
        for patient in Patient.objects.all():
            try:
                with transaction.atomic():
                    # Try to get existing index or create new one
                    index, created = PatientSearchIndex.objects.get_or_create(
                        patient=patient,
                        defaults={
                            'mrn': patient.mrn or '',
                            'national_id': patient.national_id or '',
                            'full_name': patient.get_full_name() or '',
                            'phone_mobile': patient.phone_mobile or '',
                            'phone_home': patient.phone_home or '',
                            'email': patient.email or '',
                            'date_of_birth': patient.date_of_birth,
                            'branch_id': patient.branch_id if patient.branch else None,
                        }
                    )
                    
                    if not created:
                        # Update existing index
                        index.update_from_patient()
                        index.save()
                    
                    count += 1
                    
                    if count % 10 == 0:
                        self.stdout.write(f'  Processed {count}/{total_patients} patients...')
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'  Error indexing patient {patient.id} ({patient.get_full_name()}): {str(e)}'
                ))
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully indexed {count} patients. Errors: {error_count}'
        ))