import os
from django.core.management.base import BaseCommand
from files.models import MedicalFile


class Command(BaseCommand):
    help = 'Fix file metadata for existing files'

    def handle(self, *args, **options):
        files = MedicalFile.objects.all()
        fixed_count = 0
        
        self.stdout.write(f"Found {files.count()} files to check...")
        
        for file in files:
            changed = False
            
            # Fix file extension from the file path
            if not file.file_extension and file.file:
                # Extract extension from the stored file path
                filename = os.path.basename(file.file.name)
                if '.' in filename:
                    ext = filename.split('.')[-1].lower()
                    file.file_extension = ext
                    changed = True
                    self.stdout.write(f"  Fixed extension for {file.title}: {ext}")
            
            # Fix content type based on extension
            if not file.content_type and file.file_extension:
                ext_to_type = {
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif',
                    'tiff': 'image/tiff',
                    'pdf': 'application/pdf',
                    'txt': 'text/plain',
                    'csv': 'text/csv',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }
                file.content_type = ext_to_type.get(file.file_extension, 'application/octet-stream')
                changed = True
            
            # Fix file size
            if not file.file_size and file.file:
                try:
                    file.file_size = file.file.size
                    changed = True
                except:
                    pass
            
            if changed:
                file.save(update_fields=['file_extension', 'content_type', 'file_size'])
                fixed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} files"))