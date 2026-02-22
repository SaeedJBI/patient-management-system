from django.core.management.base import BaseCommand
from files.models import MedicalFile
import hashlib


class Command(BaseCommand):
    help = 'Fix metadata for existing files'

    def handle(self, *args, **options):
        files = MedicalFile.objects.filter(file_size__isnull=True)
        count = files.count()
        
        self.stdout.write(f"Found {count} files with missing metadata")
        
        for file in files:
            try:
                if file.file and hasattr(file.file, 'size'):
                    # Set file size
                    file.file_size = file.file.size
                    
                    # Set content type if available
                    if hasattr(file.file.file, 'content_type'):
                        file.content_type = file.file.file.content_type
                    
                    # Calculate checksum
                    sha256 = hashlib.sha256()
                    file.file.seek(0)
                    for chunk in file.file.chunks():
                        sha256.update(chunk)
                    file.checksum = sha256.hexdigest()
                    file.file.seek(0)
                    
                    file.save(update_fields=['file_size', 'content_type', 'checksum'])
                    self.stdout.write(self.style.SUCCESS(f"Fixed file: {file.title}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fixing file {file.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Fixed {count} files"))