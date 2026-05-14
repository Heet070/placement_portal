"""
Management command to create the initial Super Admin for the portal.

Usage:
    python manage.py create_portal_superadmin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from portal.models import AdminProfile


class Command(BaseCommand):
    help = 'Create the initial Super Admin account for the Placement Portal'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the super admin')
        parser.add_argument('--email', type=str, help='Email for the super admin')
        parser.add_argument('--password', type=str, help='Password (prompted if not given)')
        parser.add_argument('--first-name', type=str, default='', help='First name')
        parser.add_argument('--last-name', type=str, default='', help='Last name')

    def handle(self, *args, **options):
        username = options['username'] or input('Username: ').strip()
        email = options['email'] or input('Email: ').strip()
        password = options['password']
        if not password:
            import getpass
            password = getpass.getpass('Password: ')
            confirm = getpass.getpass('Confirm password: ')
            if password != confirm:
                self.stderr.write(self.style.ERROR('Passwords do not match.'))
                return

        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(f'Username "{username}" already exists.'))
            return
        if email and User.objects.filter(email__iexact=email).exists():
            self.stderr.write(self.style.ERROR(f'Email "{email}" already registered.'))
            return

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=options.get('first_name', ''),
            last_name=options.get('last_name', ''),
        )
        AdminProfile.objects.create(user=user, role='super_admin')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Super Admin created successfully!\n'
                f'   Username : {username}\n'
                f'   Email    : {email}\n'
                f'   Role     : Super Admin\n'
                f'\nLogin at: /auth/login/'
            )
        )
