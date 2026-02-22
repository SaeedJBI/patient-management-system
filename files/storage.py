from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os


class PrivateMediaStorage(FileSystemStorage):
    """
    Custom storage class for private files.
    This ensures files are not served directly by the web server.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.PRIVATE_MEDIA_ROOT
        kwargs['base_url'] = settings.PRIVATE_MEDIA_URL
        super().__init__(*args, **kwargs)
    
    def url(self, name):
        """
        Override url method to prevent direct access.
        Returns a URL to our secure view instead of direct file URL.
        """
        # Instead of returning a direct file URL, return None
        # Files should only be accessed through our secure view
        return None