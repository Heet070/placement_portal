import secrets
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

from .models import AdminProfile
from .decorators import login_required, super_admin_required


def generate_password(length=12):
    """Generate a strong random password."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%^&*'),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


def send_account_created_email(user, password, created_by_name, site_url=''):
    """Send welcome email with login credentials."""
    subject = 'Your Placement Portal Admin Account Has Been Created'
    message = f"""
Hello {user.get_full_name() or user.username},

Your admin account for the Placement Portal has been created by {created_by_name}.

Your login credentials:
  Username: {user.username}
  Email:    {user.email}
  Password: {password}

Please log in and change your password immediately.
Login URL: {site_url}/auth/login/

If you did not expect this email, please contact your system administrator.

— Placement Portal Team
"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def send_password_reset_email(user, token, site_url=''):
    """Send password reset link email."""
    reset_url = f"{site_url}/auth/reset-password/{token}/"
    subject = 'Placement Portal – Password Reset Request'
    message = f"""
Hello {user.get_full_name() or user.username},

You requested a password reset for your Placement Portal admin account.

Click the link below to reset your password (valid for 24 hours):
{reset_url}

If you did not request a password reset, please ignore this email.

— Placement Portal Team
"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        try:
            _ = request.user.admin_profile
            return redirect('dashboard')
        except Exception:
            pass

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        # Allow login via username OR email
        user = None
        if '@' in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is not None:
            # Check they have an AdminProfile
            try:
                _ = user.admin_profile
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            except AdminProfile.DoesNotExist:
                messages.error(request, 'Your account does not have portal access.')
        else:
            messages.error(request, 'Invalid username/email or password.')

    return render(request, 'portal/auth/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')


# ─────────────────────────────────────────────
# FORGOT / RESET PASSWORD
# ─────────────────────────────────────────────

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email__iexact=email)
            profile = user.admin_profile
            token = profile.generate_reset_token()

            site_url = request.build_absolute_uri('/').rstrip('/')
            sent = send_password_reset_email(user, token, site_url)

            if sent:
                messages.success(
                    request,
                    'Password reset link has been sent to your email. Check your inbox.'
                )
            else:
                # Still show success to avoid email enumeration; log the failure
                messages.warning(
                    request,
                    'Reset link generated but email could not be sent. '
                    'Please contact your system administrator.'
                )
        except (User.DoesNotExist, AdminProfile.DoesNotExist):
            # Don't reveal whether the email exists
            messages.success(
                request,
                'If that email is registered, a reset link has been sent.'
            )
        return redirect('forgot_password')

    return render(request, 'portal/auth/forgot_password.html')


def reset_password_view(request, token):
    # Validate token
    profile = None
    try:
        profile = AdminProfile.objects.select_related('user').get(reset_token=token)
        if not profile.is_reset_token_valid(token):
            profile = None
    except AdminProfile.DoesNotExist:
        profile = None

    if profile is None:
        messages.error(request, 'This password reset link is invalid or has expired.')
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            profile.user.set_password(new_password)
            profile.user.save()
            profile.clear_reset_token()
            messages.success(request, 'Password reset successfully! Please log in.')
            return redirect('admin_login')

    return render(request, 'portal/auth/reset_password.html', {'token': token})


# ─────────────────────────────────────────────
# ADMIN MANAGEMENT (super admin only)
# ─────────────────────────────────────────────

@login_required
@super_admin_required
def admin_management_view(request):
    admins = AdminProfile.objects.select_related('user', 'created_by').order_by('role', 'user__username')
    return render(request, 'portal/auth/admin_management.html', {
        'admins': admins,
        'current_user': request.user,
    })


@login_required
@super_admin_required
def create_admin_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'admin')

        # Validate
        errors = []
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email__iexact=email).exists():
            errors.append('Email already registered.')
        if role not in ('admin', 'super_admin'):
            errors.append('Invalid role.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            password = generate_password()
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            AdminProfile.objects.create(
                user=user,
                role=role,
                created_by=request.user,
            )

            site_url = request.build_absolute_uri('/').rstrip('/')
            sent = send_account_created_email(
                user, password,
                request.user.get_full_name() or request.user.username,
                site_url
            )

            if sent:
                messages.success(
                    request,
                    f'Admin "{username}" created. Login credentials sent to {email}.'
                )
            else:
                messages.warning(
                    request,
                    f'Admin "{username}" created. '
                    f'⚠️ Email could not be sent — share the password manually: {password}'
                )

    return redirect('admin_management')


@login_required
@super_admin_required
def edit_admin_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    target_profile = get_object_or_404(AdminProfile, user=target_user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', target_profile.role)
        new_password = request.POST.get('new_password', '').strip()

        errors = []
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email__iexact=email).exclude(pk=target_user.pk).exists():
            errors.append('Email already in use by another account.')
        if role not in ('admin', 'super_admin'):
            errors.append('Invalid role.')
        if new_password and len(new_password) < 8:
            errors.append('New password must be at least 8 characters.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            target_user.first_name = first_name
            target_user.last_name = last_name
            target_user.email = email
            if new_password:
                target_user.set_password(new_password)
            target_user.save()

            target_profile.role = role
            target_profile.save()

            messages.success(request, f'Admin "{target_user.username}" updated successfully.')

    return redirect('admin_management')


@login_required
@super_admin_required
def delete_admin_view(request, user_id):
    if request.method == 'POST':
        if str(request.user.pk) == str(user_id):
            messages.error(request, 'You cannot delete your own account.')
        else:
            target_user = get_object_or_404(User, pk=user_id)
            username = target_user.username
            target_user.delete()
            messages.success(request, f'Admin "{username}" deleted successfully.')
    return redirect('admin_management')


@login_required
@super_admin_required
def resend_credentials_view(request, user_id):
    """Generate a new password and resend credentials email."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        password = generate_password()
        target_user.set_password(password)
        target_user.save()

        site_url = request.build_absolute_uri('/').rstrip('/')
        sent = send_account_created_email(
            target_user, password,
            request.user.get_full_name() or request.user.username,
            site_url
        )
        if sent:
            messages.success(request, f'New credentials sent to {target_user.email}.')
        else:
            messages.warning(
                request,
                f'Password reset. ⚠️ Email failed — share manually: {password}'
            )
    return redirect('admin_management')


# ─────────────────────────────────────────────
# CHANGE OWN PASSWORD (any admin)
# ─────────────────────────────────────────────

@login_required
def change_own_password_view(request):
    if request.method == 'POST':
        current = request.POST.get('current_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_pw) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
        elif new_pw != confirm:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_pw)
            request.user.save()
            # Re-authenticate so session isn't invalidated
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
    return redirect('dashboard')
