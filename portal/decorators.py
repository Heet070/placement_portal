from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_required(view_func):
    """Ensure user is authenticated and has an AdminProfile."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        try:
            _ = request.user.admin_profile
        except Exception:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def super_admin_required(view_func):
    """Ensure user is a super admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        try:
            if not request.user.admin_profile.is_super_admin:
                messages.error(request, 'Access denied. Super Admin privileges required.')
                return redirect('dashboard')
        except Exception:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper
