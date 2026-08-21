"""
Thin best-effort email wrapper — pattern ported from
C:\\Users\\ismai\\OneDrive\\Documents\\GitHub\\giia\\admissions\\services.py
(send_payment_confirmation_email): plain django.core.mail.send_mail, wrapped
in try/except so a bad address or a down mail server never breaks the
request/webhook/cron job that triggered it — just gets logged.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_email(subject: str, message: str, to_email: str) -> bool:
    if not to_email:
        logger.info('send_email: no recipient address given for "%s" — skipping.', subject)
        return False
    try:
        send_mail(
            subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email], fail_silently=False,
        )
        return True
    except Exception:
        logger.exception('Failed to send email "%s" to %s', subject, to_email)
        return False
