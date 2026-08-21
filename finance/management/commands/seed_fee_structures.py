"""
Seeds the real 2025/2026 fee schedule from the school's PDF — new-student
itemized fees per band, plus flat continuing-student termly fees.

Usage: python manage.py seed_fee_structures
"""

from django.core.management.base import BaseCommand, CommandError

from academics.models import AcademicSession, FeeBand
from finance.models import FeeStructure, FeeStructureItem

# (band, [(category, amount, is_optional), ...]) — new students, itemized
NEW_STUDENT_FEES = {
    'Nursery': [
        ('Tuition', 20000, False), ('Uniform', 7000, False), ('Sport Wear', 8000, False),
        ('Friday Wear (Top)', 4000, False), ('Examination', 3000, False), ('Medical', 1000, False),
        ('Stationaries', 2000, False), ('Text Books', 8000, False), ('Exercise Books', 4000, False),
        ('Jacket (optional)', 10000, True),
    ],
    'Primary': [
        ('Tuition', 23000, False), ('Uniform', 8000, False), ('Sport Wear', 9000, False),
        ('Friday Wear (Top)', 4000, False), ('Examination', 3000, False), ('Medical', 1000, False),
        ('Stationaries', 2000, False), ('Text Books', 10000, False), ('Exercise Books', 7000, False),
    ],
    'Junior Secondary': [
        ('Tuition', 25000, False), ('Uniform', 9000, False), ('Sport Wear', 15000, False),
        ('Friday Wear (Top)', 5000, False), ('Examination', 3000, False), ('Medical', 1000, False),
        ('Stationaries', 2000, False), ('Text Books', 10000, False), ('Exercise Books', 9000, False),
    ],
    'Senior Secondary': [
        ('Tuition', 30000, False), ('Uniform', 10000, False), ('Sport Wear', 15000, False),
        ('Friday Wear (Top)', 5000, False), ('Examination', 3000, False), ('Medical', 1000, False),
        ('Stationaries', 2000, False), ('Text Books', 10000, False), ('Exercise Books', 12000, False),
    ],
}

# Flat termly amount for continuing students — not itemized on the source sheet.
CONTINUING_STUDENT_FEES = {
    'Nursery': 26000, 'Primary': 29000, 'Junior Secondary': 31000, 'Senior Secondary': 36000,
}


class Command(BaseCommand):
    help = 'Seed the real fee schedule (new + continuing) for the current academic session.'

    def handle(self, *args, **options):
        session = AcademicSession.get_current()
        if not session:
            raise CommandError('No current academic session — run `python manage.py seed_academics` first.')

        created_structures = 0
        for band_name, items in NEW_STUDENT_FEES.items():
            band = FeeBand.objects.filter(name=band_name).first()
            if not band:
                self.stderr.write(self.style.WARNING(f'Fee band "{band_name}" not found — skipping.'))
                continue
            structure, made = FeeStructure.objects.get_or_create(
                session=session, fee_band=band, student_category='new',
            )
            if structure.is_locked:
                self.stdout.write(self.style.WARNING(f'{structure} is locked (invoices already generated) — leaving as-is.'))
                continue
            structure.items.all().delete()
            FeeStructureItem.objects.bulk_create([
                FeeStructureItem(fee_structure=structure, category=cat, amount=amt, is_optional=opt)
                for cat, amt, opt in items
            ])
            created_structures += 1 if made else 0

        for band_name, flat_amount in CONTINUING_STUDENT_FEES.items():
            band = FeeBand.objects.filter(name=band_name).first()
            if not band:
                continue
            structure, made = FeeStructure.objects.get_or_create(
                session=session, fee_band=band, student_category='continuing',
            )
            if structure.is_locked:
                self.stdout.write(self.style.WARNING(f'{structure} is locked (invoices already generated) — leaving as-is.'))
                continue
            structure.items.all().delete()
            FeeStructureItem.objects.create(fee_structure=structure, category='Termly Fee', amount=flat_amount)
            created_structures += 1 if made else 0

        self.stdout.write(self.style.SUCCESS(
            f'Fee structures ready for {session.name}: '
            f'{FeeStructure.objects.filter(session=session).count()} total.'
        ))
