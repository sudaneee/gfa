from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from admissions.forms import (
    AcademicInfoForm, ApplicantInfoForm, ContactInfoForm, DocumentsForm, GuardianInfoForm, TrackApplicationForm,
)
from admissions.models import Application, ApplicationInvoice
from website.models import SchoolSettings

DRAFT_SESSION_KEY = 'draft_application_id'
# Payment is deliberately the first step — an applicant must pay the
# application fee before the form unlocks, rather than paying at the end.
WIZARD_STEPS = ['payment', 'applicant', 'guardian', 'academic', 'documents', 'review']


def info(request):
    return render(request, 'admissions/info.html')


def _get_draft(request, create=True):
    draft_id = request.session.get(DRAFT_SESSION_KEY)
    if draft_id:
        draft = Application.objects.filter(pk=draft_id, is_submitted=False).first()
        if draft:
            return draft
    if not create:
        return None
    draft = Application.objects.create(
        first_name='', last_name='', date_of_birth=timezone.localdate(),
        gender='Male', state_of_origin='', lga='', parent_name='', relationship='Father',
        phone='', email='', address='', applying_for='Creche',
    )
    request.session[DRAFT_SESSION_KEY] = draft.pk
    return draft


def _get_paid_draft(request):
    """The gate every form step (past Payment) must pass: a draft must exist
    and its application-fee invoice must be paid."""
    draft = _get_draft(request, create=False)
    if not draft or not getattr(draft, 'invoice', None) or not draft.invoice.is_paid:
        return None
    return draft


def _step_url(step):
    return reverse(f'admissions:apply_{step}')


def _step_nav(current):
    current_idx = WIZARD_STEPS.index(current)
    nav = []
    for i, name in enumerate(WIZARD_STEPS):
        state = 'active' if i == current_idx else 'done' if i < current_idx else ''
        nav.append({'number': i + 1, 'label': name.capitalize(), 'state': state})
    return nav


def apply_start(request):
    """Entry point — always begins (or resumes) at the payment step."""
    return redirect('admissions:apply_payment')


def apply_continue(request, application_number, resume_token):
    """
    Durable, device-independent way back into an in-progress application —
    the link emailed once payment is confirmed (see
    payments.services._send_payment_confirmation_email). Deliberately does
    NOT depend on the browser/session that started the application: knowing
    the application_number alone isn't enough (it's sequential and shown on
    the public tracking page), so resume_token is the actual credential here,
    and it's only ever transmitted by email.
    """
    draft = Application.objects.filter(
        application_number=application_number, resume_token=resume_token,
    ).first()
    if not draft:
        messages.error(request, 'This application link is invalid or has expired.')
        return redirect('admissions:info')

    if draft.is_submitted:
        messages.info(request, 'This application has already been submitted.')
        return redirect('admissions:track')

    # Re-point this browser's session at the draft so the rest of the wizard
    # (which still uses the session for in-flight convenience) picks it up.
    request.session[DRAFT_SESSION_KEY] = draft.pk
    return redirect('admissions:apply_payment')


def apply_payment(request):
    """
    Step 1 — the application fee must be paid before the form unlocks.
    Creates the draft + its invoice on first visit (the fee is snapshotted
    from SchoolSettings right here, same as it always was — just earlier in
    the flow now).

    Before the Pay button ever shows, this collects email + phone (see
    ContactInfoForm) — without them, ZainPay's initiate call would carry a
    blank emailAddress (their docs mark it required) and any payment
    confirmation we send would have nowhere to go, including the case where
    the payment only resolves later via reconcile_zainpay or a webhook,
    after the applicant has left the page.
    """
    draft = _get_draft(request)
    school = SchoolSettings.get_solo()
    invoice, _ = ApplicationInvoice.objects.get_or_create(
        application=draft, defaults={'amount': school.application_fee},
    )

    contact_form = ContactInfoForm(instance=draft)
    if request.method == 'POST' and 'set_contact' in request.POST:
        contact_form = ContactInfoForm(request.POST, instance=draft)
        if contact_form.is_valid():
            contact_form.save()
            return redirect('admissions:apply_payment')

    context = {
        'draft': draft, 'invoice': invoice, 'step': 'payment', 'step_nav': _step_nav('payment'),
        'contact_form': contact_form, 'has_contact_info': bool(draft.email and draft.phone),
    }
    return render(request, 'admissions/apply.html', context)


def _wizard_step(request, step, form_class, template, next_step, draft, extra_ctx=None):
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES or None, instance=draft)
        if form.is_valid():
            form.save()
            return redirect(_step_url(next_step))
    else:
        form = form_class(instance=draft)

    context = {'form': form, 'step': step, 'step_nav': _step_nav(step), 'draft': draft}
    if extra_ctx:
        context.update(extra_ctx)
    return render(request, template, context)


def apply_applicant(request):
    draft = _get_paid_draft(request)
    if not draft:
        messages.info(request, 'Please pay the application fee first to begin your application.')
        return redirect('admissions:apply_payment')
    return _wizard_step(request, 'applicant', ApplicantInfoForm, 'admissions/apply.html', 'guardian', draft)


def apply_guardian(request):
    draft = _get_paid_draft(request)
    if not draft:
        return redirect('admissions:apply_payment')
    return _wizard_step(request, 'guardian', GuardianInfoForm, 'admissions/apply.html', 'academic', draft)


def apply_academic(request):
    draft = _get_paid_draft(request)
    if not draft:
        return redirect('admissions:apply_payment')
    return _wizard_step(request, 'academic', AcademicInfoForm, 'admissions/apply.html', 'documents', draft)


def apply_documents(request):
    draft = _get_paid_draft(request)
    if not draft:
        return redirect('admissions:apply_payment')
    return _wizard_step(request, 'documents', DocumentsForm, 'admissions/apply.html', 'review', draft)


def apply_review(request):
    draft = _get_paid_draft(request)
    if not draft:
        return redirect('admissions:apply_payment')

    if request.method == 'POST':
        # Final submit — the fee is already paid (step 1), so this just
        # finalizes the application itself.
        draft.is_submitted = True
        draft.submitted_at = timezone.now()
        draft.status = 'pending'
        draft.save(update_fields=['is_submitted', 'submitted_at', 'status'])
        draft.status_logs.create(stage='pending', note='Application submitted online.')

        _send_submission_confirmation_email(draft)

        del request.session[DRAFT_SESSION_KEY]
        return redirect('admissions:apply_success', application_number=draft.application_number)

    context = {'draft': draft, 'step': 'review', 'step_nav': _step_nav('review')}
    return render(request, 'admissions/apply.html', context)


def _send_submission_confirmation_email(application):
    from communication.emails import send_email

    send_email(
        subject=f'Application {application.application_number} Received',
        message=(
            f"Dear {application.parent_name},\n\n"
            f"Thank you for applying to Glittering Field Academy. Your application for "
            f"{application.full_name} ({application.applying_for}) has been received.\n\n"
            f"Application Reference: {application.application_number}\n"
            f"Current Status: Pending Review\n\n"
            "You can track your application status at any time using this reference number.\n\n"
            "Glittering Field Academy"
        ),
        to_email=application.email,
    )


def apply_success(request, application_number):
    application = get_object_or_404(Application, application_number=application_number, is_submitted=True)
    context = {'application': application, 'step': 'success'}
    return render(request, 'admissions/apply.html', context)


TRACK_STAGES = [
    ('pending', 'Submitted'),
    ('under_review', 'Under Review'),
    ('shortlisted', 'Shortlisted'),
    ('interview', 'Interview'),
    ('approved', 'Approved'),
    ('admitted', 'Admitted'),
]
TRACK_STAGE_KEYS = [k for k, _ in TRACK_STAGES]


def track(request):
    application = None
    searched = False
    if request.method == 'POST':
        form = TrackApplicationForm(request.POST)
        searched = True
        if form.is_valid():
            application = Application.objects.filter(
                application_number__iexact=form.cleaned_data['application_number'].strip(),
                is_submitted=True,
            ).first()
    else:
        form = TrackApplicationForm(initial={'application_number': request.GET.get('ref', '')})
        if request.GET.get('ref'):
            searched = True
            application = Application.objects.filter(
                application_number__iexact=request.GET['ref'], is_submitted=True,
            ).first()

    reached_stages = []
    if application and application.status in TRACK_STAGE_KEYS:
        reached_stages = TRACK_STAGE_KEYS[:TRACK_STAGE_KEYS.index(application.status) + 1]

    return render(request, 'admissions/track.html', {
        'form': form, 'application': application, 'searched': searched,
        'track_stages': TRACK_STAGES, 'reached_stages': reached_stages,
    })
