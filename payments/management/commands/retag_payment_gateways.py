"""
Management command: retag_payment_gateways

One-time (safe to re-run) audit of every payment currently tagged
gateway='zainpay' and status='success' — some of these were never actually
confirmed by ZainPay at all (the console's "Mark Received" bypasses gateway
verification entirely, and an old bug in zainpay_callback could mark an
unrelated payment successful with no verification either — see
payments/views.py::PENDING_ZAINPAY_REFERENCE_KEY). A payment tagged
'zainpay' should mean ZainPay itself confirmed it; anything else gets
retagged 'manual', which is what it actually is.

"Genuinely confirmed" means either:
  - the payment's own stored gateway_response, captured the last time
    verify_payment actually ran against it, looks like a real ZainPay
    success payload (services.looks_like_genuine_zainpay_success); or
  - asking ZainPay again right now (verify_payment) still says success.

Re-querying ZainPay is a check that ONLY ever raises confidence, never
lowers it — it doesn't reliably return data for old/settled references
(observed returning "Txn not found" even for confirmed-good payments from
weeks earlier), so a live 'not found'/'pending' answer is not on its own
treated as evidence against a payment that already has a genuine stored
response. Only a payment with neither kind of evidence gets retagged.

Retagged payments are never silently reverted to unpaid — this command
only ever changes the `gateway` label to reflect how a payment was
*actually* confirmed; it never touches `status`, `amount`, or the invoice
that payment left paid/partial. A human (the admin, via the payment's new
Edit page) decides whether the underlying amount/status also needs fixing
once the label makes the history honest.

Usage:
    python manage.py retag_payment_gateways --dry-run   # preview only
    python manage.py retag_payment_gateways              # apply
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from admissions.models import ApplicationPayment
from finance.models import Payment as FeePayment
from payments import services


class Command(BaseCommand):
    help = "Retag gateway='zainpay' successes that were never genuinely ZainPay-confirmed as gateway='manual'."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report what would change without changing anything.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        retagged = []

        for model, label_fn in (
            (ApplicationPayment, lambda p: p.invoice.application.application_number),
            (FeePayment, lambda p: f"{p.invoice.student} / {p.invoice.term}"),
        ):
            qs = model.objects.filter(gateway='zainpay', status='success').select_related('invoice')
            for payment in qs:
                if services.looks_like_genuine_zainpay_success(payment.gateway_response):
                    continue

                live_confirmed = False
                try:
                    result = services.verify_payment(payment.reference)
                    live_confirmed = result['status'] == 'success'
                except services.ZainPayError:
                    pass  # inconclusive — falls through to "no evidence found"

                if live_confirmed:
                    continue

                retagged.append((model.__name__, payment, label_fn(payment)))
                if not dry_run:
                    payment.gateway = 'manual'
                    payment.notes = (
                        payment.notes + '\n' if payment.notes else ''
                    ) + (
                        f'[System] Retagged from ZainPay to Manual on {timezone.now():%Y-%m-%d} — '
                        'no verified ZainPay confirmation found for this reference.'
                    )
                    payment.save(update_fields=['gateway', 'notes'])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Retagged (would retag, in dry-run) ===' if dry_run else '=== Retagged ==='))
        if not retagged:
            self.stdout.write('None — every zainpay-tagged success has genuine confirmation.')
        for kind, payment, label in retagged:
            self.stdout.write(f'  {kind} {payment.reference} — {label} — ₦{payment.amount:,.2f}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'{len(retagged)} payment(s) {"would be " if dry_run else ""}retagged.'))
