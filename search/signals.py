from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from patients.models import Patient
from .models import PatientSearchIndex


@receiver(post_save, sender=Patient)
def update_patient_search_index(sender, instance, created, **kwargs):
    """
    Update search index when patient is saved.
    """
    index, created = PatientSearchIndex.objects.get_or_create(patient=instance)
    index.update_from_patient()
    index.save()


@receiver(post_delete, sender=Patient)
def delete_patient_search_index(sender, instance, **kwargs):
    """
    Delete search index when patient is deleted.
    """
    PatientSearchIndex.objects.filter(patient=instance).delete()