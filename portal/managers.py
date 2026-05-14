from django.db import models


class ActiveDriveManager(models.Manager):
    """
    Custom manager that filters querysets to only include records
    linked to drives with status='active'.
    Used as the default manager on Student and Company models
    so that all main pages automatically exclude archived data.
    """

    def get_queryset(self):
        return super().get_queryset().filter(drive__status='active')
