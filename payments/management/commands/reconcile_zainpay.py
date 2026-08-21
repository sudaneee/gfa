"""
Management command: reconcile_zainpay

Queries all pending ApplicationPayment records within a configurable lookback
window and verifies each one against the ZainPay API — a safety net for any
payment whose webhook never arrived. Ported from
makarfi/src/management/commands/reconcile_zainpay.py.

Usage:
    python manage.py reconcile_zainpay

Configuration (settings.py / env):
    ZAINPAY_RECONCILE_LOOKBACK_HOURS — how far back to look (default 720 = 30 days).

Scheduling (cron — every 5 minutes):
    */5 * * * * /path/to/venv/bin/python /path/to/manage.py reconcile_zainpay >> reconcile_zainpay.log 2>&1
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from admissions.models import ApplicationPayment
from finance.models import Payment as FeePayment
from payments import services

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reconcile pending ZainPay payments (application fees + termly fees) against the ZainPay API.'

    def handle(self, *args, **options):
        lookback_hours = getattr(settings, 'ZAINPAY_RECONCILE_LOOKBACK_HOURS', 720)
        cutoff = timezone.now() - timedelta(hours=lookback_hours)
        started_at = timezone.now()

        application_qs = (
            ApplicationPayment.objects
            .filter(status='pending', gateway='zainpay', created_at__gte=cutoff)
            .select_related('invoice__application')
        )
        fee_qs = (
            FeePayment.objects
            .filter(status='pending', gateway='zainpay', created_at__gte=cutoff)
            .select_related('invoice__student')
        )
        total = application_qs.count() + fee_qs.count()

        self.stdout.write(
            f'[{started_at:%Y-%m-%d %H:%M:%S}] Starting reconciliation — '
            f'{total} pending payment(s) in the last {lookback_hours}h'
        )

        confirmed = still_pending = failed = errors = 0

        for payment in list(application_qs.iterator()) + list(fee_qs.iterator()):
            label = (
                payment.invoice.application.application_number
                if isinstance(payment, ApplicationPayment)
                else f"{payment.invoice.student} / {payment.invoice.term}"
            )
            try:
                result = services.process_payment(payment)
                if result['status'] == 'success' and result['changed']:
                    confirmed += 1
                    self.stdout.write(self.style.SUCCESS(f"CONFIRMED {payment.reference} — {label}"))
                elif result['status'] == 'failed':
                    failed += 1
                else:
                    still_pending += 1
            except services.ZainPayError as exc:
                errors += 1
                logger.error('reconcile_zainpay: API error for %s — %s', payment.reference, exc)
            except Exception as exc:
                errors += 1
                logger.exception('reconcile_zainpay: unexpected error for payment pk=%s — %s', payment.pk, exc)

        elapsed = (timezone.now() - started_at).total_seconds()
        summary = (
            f'[{timezone.now():%Y-%m-%d %H:%M:%S}] Done in {elapsed:.1f}s — '
            f'total={total} confirmed={confirmed} still_pending={still_pending} '
            f'failed={failed} errors={errors}'
        )
        self.stdout.write(summary)
