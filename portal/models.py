import secrets
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from .managers import ActiveDriveManager


class Branch(models.Model):
    branch_id = models.CharField(
        max_length=50, 
        primary_key=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]+_[A-Z]+$',
                message='Branch ID must be in the format PROGRAM_BRANCH (e.g. BTECH_CSE)'
            )
        ]
    )
    branch_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'branch'
        verbose_name_plural = 'Branches'
        ordering = ['branch_name']

    def __str__(self):
        return f"{self.branch_id} - {self.branch_name}"


class Drive(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    drive_id = models.CharField(
        max_length=50, 
        primary_key=True,
        validators=[
            RegexValidator(
                regex=r'^(SI|PD)\d{4}$',
                message='Drive ID must start with SI or PD followed by 4 digits (e.g. SI2025, PD2025).'
            )
        ]
    )
    drive_name = models.CharField(max_length=200)
    drive_year = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    branches = models.ManyToManyField(Branch, related_name='drives', blank=True)

    class Meta:
        db_table = 'drive'
        ordering = ['-drive_year', 'drive_name']

    def __str__(self):
        return f"{self.drive_name} ({self.drive_year})"

    def clean(self):
        """Enforce max 2 active drives constraint."""
        if self.status == 'active':
            active_count = Drive.objects.filter(status='active').exclude(pk=self.pk).count()
            if active_count >= 2:
                raise ValidationError(
                    'At most 2 drives may be active at a time. '
                    'Please deactivate an existing drive first.'
                )

    def save(self, *args, **kwargs):
        """Enforce max 2 active drives constraint on save."""
        if self.status == 'active':
            active_count = Drive.objects.filter(status='active').exclude(pk=self.pk).count()
            if active_count >= 2:
                raise ValidationError(
                    'At most 2 drives may be active at a time. '
                    'Please deactivate an existing drive first.'
                )
        super().save(*args, **kwargs)


class Student(models.Model):
    PLACEMENT_STATUS_CHOICES = [
        ('Unplaced', 'Unplaced'),
        ('Placed', 'Placed'),
        ('PPO', 'PPO'),
        ('Summer Internship', 'Summer Internship'),
    ]
    
    student_id = models.CharField(max_length=50, primary_key=True)
    std_name = models.CharField(max_length=200)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='students')
    drive = models.ForeignKey(Drive, on_delete=models.CASCADE, related_name='students')
    cpi = models.DecimalField(max_digits=4, decimal_places=2)
    placement_status = models.CharField(max_length=30, choices=PLACEMENT_STATUS_CHOICES, default='Unplaced')
    switch_app = models.BooleanField(default=False)
    company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='hired_students')
    profile = models.ForeignKey(
        'Profile', on_delete=models.SET_NULL, null=True, blank=True, related_name='students'
    )

    # Custom managers
    objects = ActiveDriveManager()  # Default — active drives only
    all_objects = models.Manager()  # Bypass — all data

    class Meta:
        db_table = 'student'
        ordering = ['std_name']

    def __str__(self):
        return self.std_name

    def clean(self):
        super().clean()
        if self.drive_id and self.placement_status:
            drive_id = str(self.drive_id)
            status = self.placement_status
            if drive_id.startswith('SI') and status not in ('Unplaced', 'Summer Internship'):
                raise ValidationError(
                    f'SI drives only allow "Unplaced" or "Summer Internship" status. '
                    f'Got "{status}".'
                )
            if drive_id.startswith('PD') and status not in ('Unplaced', 'Placed', 'PPO'):
                raise ValidationError(
                    f'PD drives only allow "Unplaced", "Placed", or "PPO" status. '
                    f'Got "{status}".'
                )


class Company(models.Model):
    cmp_id = models.AutoField(primary_key=True)

    cmp_name = models.CharField(max_length=200)

    drive = models.ForeignKey(
        Drive,
        on_delete=models.CASCADE,
        related_name='companies'
    )

    objects = ActiveDriveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'company'
        verbose_name_plural = 'Companies'
        ordering = ['cmp_name']

    def __str__(self):
        return self.cmp_name


class Profile(models.Model):
    OFFER_TYPE_CHOICES = [
        ('WI', 'Winter Internship'),
        ('WI+J', 'Winter Internship + Job'),
        ('J', 'Job'),
        ('SI','Summer Internship')
    ]

    profile_id = models.AutoField(primary_key=True)
    cmp = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='profiles')
    profile_name = models.CharField(max_length=200)
    ctc = models.DecimalField(max_digits=10, decimal_places=2)
    stipend = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPE_CHOICES, null=True, blank=True)

    class Meta:
        db_table = 'profile'
        ordering = ['profile_name']

    def __str__(self):
        return f"{self.profile_name} @ {self.cmp.cmp_name}"


class AdminProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('super_admin', 'Super Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_admins'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reset_token = models.CharField(max_length=128, blank=True, null=True)
    reset_token_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'admin_profile'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(48)
        self.reset_token_expires = timezone.now() + timezone.timedelta(hours=24)
        self.save()
        return self.reset_token

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires = None
        self.save()

    def is_reset_token_valid(self, token):
        return (
            self.reset_token
            and self.reset_token == token
            and self.reset_token_expires
            and timezone.now() < self.reset_token_expires
        )