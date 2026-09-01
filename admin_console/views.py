from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import inlineformset_factory, modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required
from admin_console.registry import REGISTRY, categories
from admin_console.utils import filter_lookup_value, filter_options, querystring_without_page, resolve_value


def _entry_or_404(slug):
    entry = REGISTRY.get(slug)
    if not entry:
        raise Http404(f'No manageable model registered for "{slug}".')
    return entry


@admin_required
def console_home(request):
    """Landing page for the console — every registered module grouped by
    category, plus the hand-built modules (Applications/Invoices/Payments/
    Users) that have their own dedicated pages instead of the generic form."""
    return render(request, 'admin_console/home.html', {
        'categories': categories(), 'active_nav': 'console',
    })


@admin_required
def generic_list(request, slug):
    entry = _entry_or_404(slug)
    qs = entry.model.objects.all()
    if entry.ordering:
        qs = qs.order_by(entry.ordering)

    q = request.GET.get('q', '').strip()
    if q and entry.search_fields:
        query = Q()
        for f in entry.search_fields:
            query |= Q(**{f'{f}__icontains': q})
        qs = qs.filter(query)

    active_filters = {}
    for field_name, _ in entry.filter_fields:
        val = request.GET.get(field_name)
        if val:
            qs = qs.filter(**{field_name: filter_lookup_value(entry.model, field_name, val)})
            active_filters[field_name] = val

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    rows = [{'obj': obj, 'cells': [resolve_value(obj, path) for path, _ in entry.list_fields]} for obj in page_obj]

    return render(request, 'admin_console/list.html', {
        'entry': entry, 'page_obj': page_obj, 'rows': rows, 'q': q,
        'active_filters': active_filters,
        'filters': [(name, label, filter_options(entry.model, name), active_filters.get(name, ''))
                    for name, label in entry.filter_fields],
        'active_nav': 'console', 'active_slug': slug, 'querystring': querystring_without_page(request),
    })


@admin_required
def generic_create(request, slug):
    entry = _entry_or_404(slug)
    Form = modelform_factory(entry.model, fields=entry.form_fields)
    if request.method == 'POST':
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'{entry.singular} created.')
            return redirect('admin_console:list', slug=slug)
    else:
        form = Form()
    return render(request, 'admin_console/form.html', {
        'entry': entry, 'form': form, 'mode': 'create', 'active_nav': 'console', 'active_slug': slug,
    })


@admin_required
def generic_edit(request, slug, pk):
    entry = _entry_or_404(slug)
    instance = get_object_or_404(entry.model, pk=pk)
    Form = modelform_factory(entry.model, fields=entry.form_fields)
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'{entry.singular} updated.')
            return redirect('admin_console:list', slug=slug)
    else:
        form = Form(instance=instance)
    return render(request, 'admin_console/form.html', {
        'entry': entry, 'form': form, 'mode': 'edit', 'instance': instance, 'active_nav': 'console', 'active_slug': slug,
    })


@admin_required
def generic_delete(request, slug, pk):
    entry = _entry_or_404(slug)
    if not entry.can_delete:
        raise Http404(f'{entry.label} cannot be deleted from the console.')
    instance = get_object_or_404(entry.model, pk=pk)
    if request.method == 'POST':
        label = str(instance)
        instance.delete()
        messages.success(request, f'{entry.singular} "{label}" deleted.')
        return redirect('admin_console:list', slug=slug)
    return render(request, 'admin_console/confirm_delete.html', {
        'entry': entry, 'instance': instance, 'active_nav': 'console', 'active_slug': slug,
    })


# ── Applications — dedicated, not generic: status changes must go through
# Application.set_status() so the status log / any future notifications
# keep working, exactly like the Django admin's own actions. ─────────────

@admin_required
def applications_list(request):
    from admissions.models import Application

    qs = Application.objects.filter(is_submitted=True).order_by('-submitted_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(application_number__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(parent_name__icontains=q) | Q(phone__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/applications.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': Application.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'applications',
        'querystring': querystring_without_page(request),
    })


@admin_required
def application_detail(request, pk):
    from admissions.models import Application

    application = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Application.STATUS_CHOICES):
            application.set_status(new_status, note=f'Marked {dict(Application.STATUS_CHOICES)[new_status]} via Superadmin Console.', user=request.user)
            messages.success(request, f'Application marked as {application.get_status_display()}.')
            return redirect('admin_console:application_detail', pk=pk)
        messages.error(request, 'Invalid status.')

    return render(request, 'admin_console/application_detail.html', {
        'application': application, 'status_choices': Application.STATUS_CHOICES,
        'status_logs': application.status_logs.order_by('-created_at'),
        'enrolled_student': getattr(application, 'student', None),
        'active_nav': 'console', 'active_slug': 'applications',
    })


def _unique_username(seed: str) -> str:
    """Slugify a name/email into a username, appending a number if taken —
    same idea as makarfi's username generation, simplified."""
    import re

    from accounts.models import User

    base = re.sub(r'[^a-z0-9]+', '.', seed.lower()).strip('.') or 'parent'
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'
    return username


@admin_required
def application_enroll(request, pk):
    """
    Turns an admitted Application into a real, enrolled Student — the one
    piece of the admissions flow that was previously entirely manual (see
    students.models.Student.application's docstring: the field existed for
    this from the start, nothing ever populated it). Reuses an existing
    Guardian by phone/email when one already exists (siblings), and reuses
    finance.services.generate_invoice rather than re-deriving fee logic.
    """
    from academics.models import Section, Term
    from accounts.models import User
    from admissions.models import Application
    from communication.emails import send_email
    from django.conf import settings as django_settings
    from finance.services import InvoiceGenerationError, generate_invoice
    from students.models import Guardian, Student

    application = get_object_or_404(Application, pk=pk)

    if application.status != 'admitted':
        messages.error(request, 'Mark this application "Admitted" before enrolling the student.')
        return redirect('admin_console:application_detail', pk=pk)

    existing_student = getattr(application, 'student', None)
    if existing_student:
        messages.info(request, f'{application.full_name} is already enrolled as {existing_student}.')
        return redirect('admin_console:edit', 'students', existing_student.pk)

    sections = Section.objects.select_related('school_class').order_by('school_class__order', 'name')
    suggested_section = sections.filter(school_class__name=application.applying_for).first()

    if request.method == 'POST':
        section = get_object_or_404(Section, pk=request.POST.get('section'))
        create_login = request.POST.get('create_login') == 'on'

        guardian = Guardian.objects.filter(
            Q(email__iexact=application.email) | Q(phone=application.phone)
        ).first()
        if not guardian:
            guardian = Guardian.objects.create(
                name=application.parent_name, relationship=application.relationship,
                phone=application.phone, email=application.email,
                address=application.address, occupation=application.occupation,
            )

        credentials_note = ''
        if create_login and not guardian.user_id:
            import secrets

            first, _, last = application.parent_name.partition(' ')
            username = _unique_username(application.email or application.parent_name)
            password = secrets.token_urlsafe(9)
            user = User.objects.create_user(
                username=username, email=application.email, first_name=first, last_name=last,
                password=password, role='parent',
            )
            guardian.user = user
            guardian.save(update_fields=['user'])

            from website.models import SchoolSettings

            login_url = f"{django_settings.SITE_URL}{reverse('accounts:login')}"
            sent = send_email(
                subject=f"Your Parent Portal login — {SchoolSettings.get_solo().name}",
                message=(
                    f"Dear {application.parent_name},\n\n"
                    f"{application.first_name} has been enrolled. You can now sign in to the Parent Portal "
                    f"to track results, attendance and fees.\n\n"
                    f"Login: {login_url}\nUsername: {username}\nPassword: {password}\n\n"
                    f"Please keep these details safe."
                ),
                to_email=application.email,
            )
            credentials_note = ' Parent login created and emailed.' if sent else \
                f' Parent login created (username: {username}, password: {password}) — email could not be sent, share these manually.'

        student = Student.objects.create(
            first_name=application.first_name, last_name=application.last_name,
            gender=application.gender, date_of_birth=application.date_of_birth,
            school_class=section.school_class, section=section,
            guardian=guardian, status='Active', application=application,
        )

        invoice_note = ''
        term = Term.get_current()
        if term:
            try:
                generate_invoice(student, term)
                invoice_note = f' Invoice generated for {term}.'
            except InvoiceGenerationError as exc:
                invoice_note = f' Could not generate an invoice: {exc}'
        else:
            invoice_note = ' No current term is set, so no invoice was generated — do that from Fees once one is.'

        messages.success(request, f'{student} enrolled successfully.{credentials_note}{invoice_note}')
        return redirect('admin_console:edit', 'students', student.pk)

    return render(request, 'admin_console/application_enroll.html', {
        'application': application, 'sections': sections, 'suggested_section': suggested_section,
        'active_nav': 'console', 'active_slug': 'applications',
    })


# ── Invoices — read-only in the console; invoices are generated (frozen
# items), never hand-edited. "View" reuses the existing parent-facing
# invoice page, which already supports admin viewing. ────────────────────

@admin_required
def invoices_list(request):
    from finance.models import Invoice

    qs = Invoice.objects.select_related('student', 'term').order_by('-generated_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) | Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) | Q(student__admission_number__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/invoices_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': Invoice.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'invoices',
        'querystring': querystring_without_page(request),
    })


# ── Payments — list + a "Mark Received" action for pending/manual ones,
# reusing finance.services.mark_payment_success (also used by the admin's
# own save_model, see finance/admin.py) so behaviour never drifts. ───────

@admin_required
def payments_list(request):
    from finance.models import Payment

    qs = Payment.objects.select_related('invoice__student').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) | Q(gateway_reference__icontains=q) |
            Q(receipt_number__icontains=q) | Q(invoice__student__first_name__icontains=q) |
            Q(invoice__student__last_name__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    gateway = request.GET.get('gateway', '')
    if gateway:
        qs = qs.filter(gateway=gateway)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/payments_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status, 'gateway': gateway,
        'status_choices': Payment.STATUS_CHOICES, 'gateway_choices': Payment.GATEWAY_CHOICES,
        'active_nav': 'console', 'active_slug': 'payments',
        'querystring': querystring_without_page(request),
    })


@admin_required
def payment_mark_received(request):
    if request.method != 'POST':
        raise Http404
    from finance.models import Payment
    from finance.services import mark_payment_success

    payment = get_object_or_404(Payment, pk=request.POST.get('pk'))
    mark_payment_success(payment, request.user)
    messages.success(request, f'Payment {payment.reference} marked received — invoice status updated.')

    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:payments_list')}{'?' + qs if qs else ''}")


# ── Fee Structures — the one deliberately non-generic financial-config
# model: editing/deleting must stop dead once a structure has been used to
# generate an invoice (is_locked), so an already-billed amount can never
# retroactively change. That's exactly the guarantee FeeStructure.lock()
# already enforces (see finance/services.py::generate_invoice) — the
# console just respects `is_locked` rather than re-deriving it. ─────────

def _fee_structure_formset_factory():
    from finance.models import FeeStructure, FeeStructureItem
    return inlineformset_factory(
        FeeStructure, FeeStructureItem, fields=['category', 'amount', 'is_optional'],
        extra=1, can_delete=True,
    )


@admin_required
def fee_structures_list(request):
    from finance.models import FeeStructure

    qs = FeeStructure.objects.select_related('session', 'fee_band').order_by('-session__name', 'fee_band__name')
    session = request.GET.get('session', '')
    if session:
        qs = qs.filter(session_id=session)
    locked = request.GET.get('locked', '')
    if locked == 'yes':
        qs = qs.filter(is_locked=True)
    elif locked == 'no':
        qs = qs.filter(is_locked=False)

    from academics.models import AcademicSession
    return render(request, 'admin_console/fee_structures_list.html', {
        'structures': qs, 'sessions': AcademicSession.objects.all(), 'session': session, 'locked': locked,
        'active_nav': 'console', 'active_slug': 'fee-structures',
    })


@admin_required
def fee_structure_create(request):
    from finance.models import FeeStructure

    FeeStructureForm = modelform_factory(FeeStructure, fields=['session', 'fee_band', 'student_category'])
    ItemFormSet = _fee_structure_formset_factory()

    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        formset = ItemFormSet(request.POST, instance=FeeStructure())
        if form.is_valid():
            structure = form.save(commit=False)
            formset = ItemFormSet(request.POST, instance=structure)
            if formset.is_valid():
                structure.save()
                formset.save()
                messages.success(request, 'Fee structure created.')
                return redirect('admin_console:fee_structures_list')
    else:
        form = FeeStructureForm()
        formset = ItemFormSet(instance=FeeStructure())

    return render(request, 'admin_console/fee_structure_form.html', {
        'form': form, 'formset': formset, 'mode': 'create', 'structure': None,
        'active_nav': 'console', 'active_slug': 'fee-structures',
    })


@admin_required
def fee_structure_edit(request, pk):
    from finance.models import FeeStructure

    structure = get_object_or_404(FeeStructure, pk=pk)
    if structure.is_locked:
        messages.error(request, 'This fee structure has already generated invoices, so its identity and items are locked — create a new one instead of editing this one.')
        return redirect('admin_console:fee_structures_list')

    FeeStructureForm = modelform_factory(FeeStructure, fields=['session', 'fee_band', 'student_category'])
    ItemFormSet = _fee_structure_formset_factory()

    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=structure)
        formset = ItemFormSet(request.POST, instance=structure)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Fee structure updated.')
            return redirect('admin_console:fee_structures_list')
    else:
        form = FeeStructureForm(instance=structure)
        formset = ItemFormSet(instance=structure)

    return render(request, 'admin_console/fee_structure_form.html', {
        'form': form, 'formset': formset, 'mode': 'edit', 'structure': structure,
        'active_nav': 'console', 'active_slug': 'fee-structures',
    })


@admin_required
def fee_structure_delete(request, pk):
    from finance.models import FeeStructure

    structure = get_object_or_404(FeeStructure, pk=pk)
    if structure.is_locked:
        messages.error(request, 'This fee structure has already generated invoices and cannot be deleted.')
        return redirect('admin_console:fee_structures_list')

    if request.method == 'POST':
        label = str(structure)
        structure.delete()
        messages.success(request, f'Fee structure "{label}" deleted.')
        return redirect('admin_console:fee_structures_list')

    return render(request, 'admin_console/confirm_delete_simple.html', {
        'label': str(structure), 'cancel_url': 'admin_console:fee_structures_list',
        'active_nav': 'console', 'active_slug': 'fee-structures',
    })
