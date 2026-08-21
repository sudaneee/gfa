"""
Generates fee invoices for every active student for a term — the termly
billing run. Idempotent: students who already have an invoice for the term
are skipped, not duplicated or re-priced.

Usage:
    python manage.py generate_term_invoices             # current term
    python manage.py generate_term_invoices --term-id 3
"""

from django.core.management.base import BaseCommand, CommandError

from academics.models import Term
from finance.services import generate_invoices_for_term


class Command(BaseCommand):
    help = 'Generate fee invoices for all active students for a term (default: current term).'

    def add_arguments(self, parser):
        parser.add_argument('--term-id', type=int, default=None)

    def handle(self, *args, **options):
        term = Term.objects.filter(pk=options['term_id']).first() if options['term_id'] else Term.get_current()
        if not term:
            raise CommandError('No current term set and no --term-id given.')

        summary = generate_invoices_for_term(term)
        self.stdout.write(self.style.SUCCESS(
            f"{term}: {summary['created']} invoice(s) created, "
            f"{summary['skipped']} already existed, {len(summary['errors'])} error(s)."
        ))
        for error in summary['errors']:
            self.stderr.write(self.style.WARNING(error))
