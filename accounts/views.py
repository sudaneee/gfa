from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.forms import AdminCreateUserForm, ApplicantSignupForm


def _authenticate_by_identifier(request, identifier, password):
    """Shared by login_view and admissions' applicant_login — accepts a
    username OR an email address in the one field, since most people type
    their email."""
    user = authenticate(request, username=identifier, password=password)
    if user is not None:
        return user
    from accounts.models import User
    try:
        match = User.objects.get(email__iexact=identifier)
    except User.DoesNotExist:
        return None
    return authenticate(request, username=match.username, password=password)


def login_view(request):
    """
    The School Portal login — staff, teachers, and parents/students of
    already-enrolled children. Deliberately separate from
    admissions.views.applicant_login: an applicant only cares about their
    application(s), not the full staff/parent dashboard, and shouldn't
    have to find their way through that unrelated furniture to get there.
    """
    if request.user.is_authenticated:
        return redirect('portal:home')

    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = _authenticate_by_identifier(request, identifier, password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or request.POST.get('next')
            return redirect(next_url or 'portal:home')

        messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html')


def applicant_signup(request):
    """
    Create an account to apply — one login, many children. Reuses (links)
    an existing user-less Guardian record when one already exists for this
    phone/email (an admin-managed record from an already-enrolled sibling,
    say) instead of duplicating it; rejects outright if that Guardian is
    already linked to an account. New signups get role='parent' from the
    start — an applicant account *is* a parent account, so there's never a
    second login once a child is later admitted and enrolled.
    """
    from students.models import Guardian

    if request.method == 'POST':
        form = ApplicantSignupForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone'].strip()
            email = form.cleaned_data['email']
            full_name = form.cleaned_data['full_name'].strip()

            guardian = Guardian.objects.filter(Q(email__iexact=email) | Q(phone=phone)).first()
            if guardian and guardian.user_id:
                form.add_error(None, 'An account already exists for this email/phone — log in instead.')
            else:
                from accounts.models import User

                user = User.objects.create_user(
                    username=email, email=email, password=form.cleaned_data['password1'], role='parent',
                )
                first, _, last = full_name.partition(' ')
                user.first_name, user.last_name = first, last
                user.save(update_fields=['first_name', 'last_name'])

                if guardian:
                    guardian.name, guardian.phone, guardian.email, guardian.user = full_name, phone, email, user
                    guardian.save(update_fields=['name', 'phone', 'email', 'user'])
                else:
                    Guardian.objects.create(name=full_name, phone=phone, email=email, user=user)

                login(request, user)
                messages.success(request, f'Welcome, {full_name}! You can now apply for your child.')
                next_url = request.POST.get('next')
                return redirect(next_url or 'admissions:dashboard')
    else:
        form = ApplicantSignupForm()

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('website:home')


@admin_required
def user_list(request):
    """Users & Roles — the one piece of user/permission management that
    previously only existed in the raw Django admin. Search + role/status
    filter, and per-row role-change / activate-deactivate actions that stay
    on this page (redirect preserves the current filter querystring)."""
    from accounts.models import User

    users = User.objects.all().order_by('-date_joined')

    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')

    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    if role:
        users = users.filter(role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)

    role_counts = {row['role']: row['count'] for row in User.objects.values('role').annotate(count=Count('id'))}

    return render(request, 'accounts/user_list.html', {
        'users': users, 'q': q, 'role': role, 'status': status,
        'roles': User.Role.choices, 'role_counts': role_counts,
        'total_users': User.objects.count(), 'active_users': User.objects.filter(is_active=True).count(),
        'querystring': request.GET.urlencode(), 'active_nav': 'users',
    })


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = AdminCreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'{user.get_full_name() or user.username} created as {user.get_role_display()}.')
            return redirect('accounts:user_list')
    else:
        form = AdminCreateUserForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'active_nav': 'users'})


@admin_required
@require_POST
def user_toggle_active(request, pk):
    from accounts.models import User

    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You can't deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        messages.success(request, f"{target.get_full_name() or target.username} is now {'active' if target.is_active else 'inactive'}.")

    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('accounts:user_list')}{'?' + qs if qs else ''}")


@admin_required
@require_POST
def user_update_role(request, pk):
    from accounts.models import User

    target = get_object_or_404(User, pk=pk)
    new_role = request.POST.get('role')
    if new_role not in dict(User.Role.choices):
        messages.error(request, 'Invalid role selected.')
    elif target == request.user and new_role != User.Role.ADMIN:
        messages.error(request, "You can't remove your own administrator role.")
    else:
        target.role = new_role
        target.save(update_fields=['role'])
        messages.success(request, f"{target.get_full_name() or target.username}'s role is now {target.get_role_display()}.")

    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('accounts:user_list')}{'?' + qs if qs else ''}")
