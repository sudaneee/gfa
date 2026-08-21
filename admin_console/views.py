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
