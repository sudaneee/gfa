"""
Payment views. Two payment kinds share this module because they share the
exact same ZainPay flow (payments.services):

  - Admission application fees (ApplicationPayment) — applicants aren't
    authenticated users, so looked up by application_number, same trust
    model as the public tracking page.
  - Termly school fees (finance.Payment) — looked up by student/term, gated
    to the owning parent/student (or staff) via role_required.

ZainPay's callback/webhook doesn't know which kind a given txnRef belongs
to, so zainpay_callback/zainpay_webhook resolve the reference across both
tables via find_payment_by_reference().
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from admissions.models import Application, ApplicationPayment
from academics.models import Term
from finance.models import Payment as FeePayment
from payments import services
from students.models import Student

logger = logging.getLogger(__name__)


def find_payment_by_reference(reference):
    if not reference:
        return None
    payment = ApplicationPayment.objects.filter(reference=reference).first()
    if payment:
        return payment
    return FeePayment.objects.filter(reference=reference).first()


def _application_redirect_url(application):
    """
    Mid-wizard (fee just paid, form not filled in/submitted yet) → back into
    the wizard so "Continue" unlocks. Already-submitted (e.g. a retry on an
    edge case, or paying an outstanding balance after the fact) → the
    standalone invoice page.
    """
    if not application.is_submitted:
        return reverse('admissions:apply_payment')
    return reverse('payments:application_invoice', args=[application.application_number])


def _redirect_url_for(payment):
    if isinstance(payment, ApplicationPayment):
        return _application_redirect_url(payment.invoice.application)
    return reverse('payments:fee_invoice', args=[payment.invoice.student_id, payment.invoice.term_id])


# ── Admission application fees ────────────────────────────────────────────────
# Note: these are no longer gated on is_submitted=True — payment happens
# *before* the applicant fills in and submits the form (see admissions.views),
# so the invoice/payment already exist against a draft (unsubmitted) Application.

def application_invoice(request, application_number):
    application = get_object_or_404(Application, application_number=application_number)
    invoice = getattr(application, 'invoice', None)
    return render(request, 'payments/application_invoice.html', {
        'application': application, 'invoice': invoice,
    })


@require_POST
def initiate_application_payment(request, application_number):
    application = get_object_or_404(Application, application_number=application_number)
    invoice = getattr(application, 'invoice', None)

    if not invoice or invoice.is_paid:
        messages.info(request, 'This application fee is already paid.')
        return redirect(_application_redirect_url(application))

    callback_url = request.build_absolute_uri(reverse('payments:zainpay_callback'))
    try:
        result = services.initiate_payment(
            invoice=invoice, callback_url=callback_url, customer_email=application.email,
            mobile=application.phone or '08000000000',
        )
    except services.ZainPayError as exc:
        logger.error('ZainPay initiate failed for %s: %s', application_number, exc)
        messages.error(request, f'Payment gateway error: {exc}')
        return redirect(_application_redirect_url(application))

    ApplicationPayment.objects.create(
        invoice=invoice, amount=invoice.balance, gateway='zainpay', status='pending',
        gateway_reference=result['gateway_reference'], reference=result['reference'],
    )
    return redirect(result['payment_url'])


@require_POST
def check_application_payment_status(request, application_number, payment_pk):
    application = get_object_or_404(Application, application_number=application_number)
    payment = get_object_or_404(ApplicationPayment, pk=payment_pk, invoice__application=application)
    if payment.status == 'success':
        messages.info(request, 'This payment is already confirmed as successful.')
        return redirect(_application_redirect_url(application))
    try:
        result = services.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, 'Payment confirmed!')
        else:
            messages.info(request, f'Payment status: {result["status"]}.')
    except services.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')
    return redirect(_application_redirect_url(application))


# ── Termly school fees ────────────────────────────────────────────────────────

def _can_view_fee_invoice(user, student):
    if user.role in ('admin', 'teacher'):
        return True
    if user.role == 'parent':
        return student.guardian_id and student.guardian.user_id == user.id
    if user.role == 'student':
        return student.user_id == user.id
    return False


@role_required('admin', 'teacher', 'parent', 'student')
def fee_invoice(request, student_id, term_id):
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(Term, pk=term_id)
    if not _can_view_fee_invoice(request.user, student):
        messages.error(request, 'You do not have permission to view that invoice.')
        return render(request, 'payments/fee_invoice.html', {'forbidden': True})

    invoice = student.invoices.filter(term=term).first()
    return render(request, 'payments/fee_invoice.html', {
        'student': student, 'term': term, 'invoice': invoice,
    })


@role_required('admin', 'teacher', 'parent', 'student')
@require_POST
def initiate_fee_payment(request, student_id, term_id):
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(Term, pk=term_id)
    if not _can_view_fee_invoice(request.user, student):
        messages.error(request, 'You do not have permission to pay that invoice.')
        return redirect('portal:home')

    invoice = student.invoices.filter(term=term).first()
    if not invoice or invoice.is_paid:
        messages.info(request, 'This invoice is already paid.')
        return redirect('payments:fee_invoice', student_id=student_id, term_id=term_id)

    callback_url = request.build_absolute_uri(reverse('payments:zainpay_callback'))
    guardian = student.guardian
    email = (guardian.email if guardian and guardian.email else request.user.email) or 'parent@example.com'
    mobile = (guardian.phone if guardian else '') or '08000000000'

    try:
        result = services.initiate_payment(invoice=invoice, callback_url=callback_url, customer_email=email, mobile=mobile)
    except services.ZainPayError as exc:
        logger.error('ZainPay initiate failed for student=%s term=%s: %s', student_id, term_id, exc)
        messages.error(request, f'Payment gateway error: {exc}')
        return redirect('payments:fee_invoice', student_id=student_id, term_id=term_id)

    FeePayment.objects.create(
        invoice=invoice, amount=invoice.balance, gateway='zainpay', status='pending',
        gateway_reference=result['gateway_reference'], reference=result['reference'],
    )
    return redirect(result['payment_url'])


@role_required('admin', 'teacher', 'parent', 'student')
@require_POST
def check_fee_payment_status(request, student_id, term_id, payment_pk):
    student = get_object_or_404(Student, pk=student_id)
    if not _can_view_fee_invoice(request.user, student):
        messages.error(request, 'You do not have permission to view that payment.')
        return redirect('portal:home')
    payment = get_object_or_404(FeePayment, pk=payment_pk, invoice__student=student)
    return _check_status(request, payment, 'payments:fee_invoice', student_id=student_id, term_id=term_id)


def _check_status(request, payment, redirect_name, **redirect_kwargs):
    if payment.status == 'success':
        messages.info(request, 'This payment is already confirmed as successful.')
        return redirect(redirect_name, **redirect_kwargs)
    try:
        result = services.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, 'Payment confirmed!')
        else:
            messages.info(request, f'Payment status: {result["status"]}.')
    except services.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')
    return redirect(redirect_name, **redirect_kwargs)


# ── ZainPay callback / webhook (shared by both payment kinds) ────────────────

@csrf_exempt
def zainpay_callback(request):
    """
    Dual-purpose endpoint:
      - POST, unauthenticated server push → ZainPay webhook.
      - GET → browser redirect back after the hosted checkout, verify + update.
    """
    if request.method == 'POST':
        return zainpay_webhook(request)

    txn_ref = request.GET.get('txnRef') or request.GET.get('reference')
    payment = find_payment_by_reference(txn_ref)
    if not payment:
        # Fall back to the most recent pending payment if txnRef didn't come
        # through — graceful degradation on the redirect-back leg only.
        payment = (
            ApplicationPayment.objects.filter(status='pending').order_by('-created_at').first()
            or FeePayment.objects.filter(status='pending').order_by('-created_at').first()
        )
    if not payment:
        messages.warning(request, 'No pending payment found to verify.')
        return redirect('website:home')

    try:
        result = services.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, f'Payment of ₦{payment.amount:,.2f} confirmed. Thank you!')
        elif result['status'] == 'pending':
            messages.info(request, 'Payment is still processing — please check again shortly.')
        else:
            messages.error(request, 'Payment was not successful. Please try again.')
    except services.ZainPayError as exc:
        logger.error('ZainPay verify failed for %s: %s', payment.reference, exc)
        messages.error(request, f'Could not verify payment: {exc}')

    return redirect(_redirect_url_for(payment))


def zainpay_webhook(request):
    """
    Receives server-to-server deposit event notifications from ZainPay.
    Always returns 200 so ZainPay stops retrying — errors are logged only.
    Ported from makarfi/src/views/applicant_views.py::zainpay_webhook.
    """
    raw_body = request.body
    logger.info('ZainPay webhook received — body=%s', raw_body[:500])

    try:
        secret_key = getattr(settings, 'ZAINPAY_SECRET_KEY', '')
        if secret_key:
            received_sig = request.headers.get('Zainpay-Signature', '')
            expected_sig = hmac.new(secret_key.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, received_sig):
                logger.warning('ZainPay webhook: invalid signature received=%s', received_sig)
                return JsonResponse({'status': 'error', 'reason': 'invalid signature'}, status=400)

        if not raw_body:
            return JsonResponse({'status': 'ok', 'reason': 'empty body'}, status=200)

        try:
            payload = json.loads(raw_body)
        except (ValueError, TypeError):
            logger.warning('ZainPay webhook: non-JSON body — %s', raw_body[:300])
            return JsonResponse({'status': 'ok', 'reason': 'invalid JSON'}, status=200)

        event = payload.get('event') or payload.get('event_type', '')
        data = payload.get('data') or {}
        txn_ref = data.get('txnRef') or payload.get('txnRef', '')

        logger.info('ZainPay webhook event=%s txnRef=%s', event, txn_ref)

        if 'deposit' not in event:
            return JsonResponse({'status': 'ok', 'reason': f'event {event!r} not processed'}, status=200)
        if not txn_ref:
            return JsonResponse({'status': 'ok', 'reason': 'no txnRef'}, status=200)

        payment = find_payment_by_reference(txn_ref)
        if not payment:
            logger.warning('ZainPay webhook: no payment for txnRef=%s', txn_ref)
            return JsonResponse({'status': 'ok', 'reason': 'payment not found'}, status=200)

        if payment.status == 'success':
            return JsonResponse({'status': 'ok', 'reason': 'already confirmed'}, status=200)

        try:
            services.process_payment(payment)
        except services.ZainPayError as exc:
            logger.error('ZainPay webhook verify API error for %s: %s', txn_ref, exc)

    except Exception as exc:
        logger.exception('ZainPay webhook unhandled error: %s', exc)

    return JsonResponse({'status': 'ok'}, status=200)
