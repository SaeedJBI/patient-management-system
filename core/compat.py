"""
Compatibility patches for Python 3.14+ and Django 4.2.x

This module contains workarounds for compatibility issues between
Python 3.14 and Django 4.2.x. These can be removed when:
1. Django releases a version with official Python 3.14 support, or
2. We upgrade to a Django version that supports Python 3.14
"""
from django.template import context

def apply_patches():
    """
    Apply all necessary compatibility patches for Python 3.14
    """
    # Patch Django's Context class __copy__ method for Python 3.14 compatibility
    # This fixes: 'super' object has no attribute 'dicts' error
    original_copy = context.Context.__copy__
    
    def patched_copy(self):
        """
        Create a copy of the context by directly accessing dicts
        instead of relying on super().__copy__() which fails in Python 3.14
        """
        # Create a new context with the same dicts
        new_context = context.Context(self.dicts)
        return new_context
    
    # Apply the patch
    context.Context.__copy__ = patched_copy
    
    # Optional: Log that patches were applied
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Applied Python 3.14 compatibility patches for Django template context")