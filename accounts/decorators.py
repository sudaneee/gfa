"""
Role-gating decorators — ported from makarfi/src/decorators/auth.py.

Same shape (a decorator factory over request.user.role), narrowed to this
school's four roles instead of a tertiary ERP's long staff-title list.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    """Restrict a view to users whose `.role` is one of `roles`."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please log in to access this page.')
                return redirect(f"/login/?next={request.path}")
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('portal:home')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# ── Convenient shortcuts ──────────────────────────────────────────────────────

admin_required = role_required('admin')
teacher_required = role_required('teacher')
parent_required = role_required('parent')
student_required = role_required('student')
staff_required = role_required('admin', 'teacher')
