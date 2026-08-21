"""
Seeds the core academic structure: the current session/term, the 4 real fee
bands from the PDF fee schedule, all 16 classes with sections, and subjects
per level — matching what the frontend prototype hardcoded in
assets/js/data.js (CLASS_LIST / SUBJECTS_BY_LEVEL), now as real rows.

Usage: python manage.py seed_academics
"""

from django.core.management.base import BaseCommand

from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Subject, Term
from website.models import SchoolSettings

CLASS_LIST = [
    ('Creche', 'Creche', ['A'], 'Nursery'),
    ('Pre-Nursery', 'Pre-Nursery', ['A'], 'Nursery'),
    ('Nursery 1', 'Nursery', ['A'], 'Nursery'),
    ('Nursery 2', 'Nursery', ['A'], 'Nursery'),
    ('Primary 1', 'Primary', ['A', 'B'], 'Primary'),
    ('Primary 2', 'Primary', ['A', 'B'], 'Primary'),
    ('Primary 3', 'Primary', ['A', 'B'], 'Primary'),
    ('Primary 4', 'Primary', ['A', 'B'], 'Primary'),
    ('Primary 5', 'Primary', ['A', 'B'], 'Primary'),
    ('Primary 6', 'Primary', ['A', 'B'], 'Primary'),
    ('JSS 1', 'Secondary', ['A', 'B'], 'Junior Secondary'),
    ('JSS 2', 'Secondary', ['A', 'B'], 'Junior Secondary'),
    ('JSS 3', 'Secondary', ['A', 'B'], 'Junior Secondary'),
    ('SSS 1', 'Secondary', ['A', 'B'], 'Senior Secondary'),
    ('SSS 2', 'Secondary', ['A', 'B'], 'Senior Secondary'),
    ('SSS 3', 'Secondary', ['A', 'B'], 'Senior Secondary'),
]

SUBJECTS_BY_LEVEL = {
    'Creche': ['Numeracy', 'Literacy', 'Rhymes & Music', 'Creative Arts'],
    'Pre-Nursery': ['Numeracy', 'Literacy', 'Phonics', 'Creative Arts', 'Social Habits'],
    'Nursery': ['Numeracy', 'Literacy', 'Phonics', 'Creative Arts', 'Social Habits', 'Physical Education'],
    'Primary': ['English Studies', 'Mathematics', 'Basic Science', 'Social Studies', 'Civic Education',
                'Computer Studies', 'Agricultural Science', 'Home Economics', 'Physical & Health Education',
                'CRS', 'Fine Arts'],
    'Secondary': ['English Language', 'Mathematics', 'Basic Science', 'Basic Technology', 'Business Studies',
                  'Social Studies', 'Civic Education', 'Computer Studies', 'French', 'Agricultural Science',
                  'CRS', 'Physical & Health Education'],
}


class Command(BaseCommand):
    help = 'Seed academic sessions/terms, fee bands, classes, sections and subjects.'

    def handle(self, *args, **options):
        school = SchoolSettings.get_solo()

        session, _ = AcademicSession.objects.get_or_create(name=school.current_session, defaults={'is_current': True})
        if not AcademicSession.objects.filter(is_current=True).exists():
            session.is_current = True
            session.save()
        term, _ = Term.objects.get_or_create(session=session, name='first', defaults={'is_current': True})
        if not Term.objects.filter(is_current=True).exists():
            term.is_current = True
            term.save()
        self.stdout.write(self.style.SUCCESS(f'Session: {session.name} — Current term: {term.get_name_display()}'))

        bands = {}
        for name in ['Nursery', 'Primary', 'Junior Secondary', 'Senior Secondary']:
            band, _ = FeeBand.objects.get_or_create(name=name)
            bands[name] = band
        self.stdout.write(self.style.SUCCESS(f'Fee bands: {", ".join(bands)}'))

        for order, (name, level, sections, band_name) in enumerate(CLASS_LIST):
            school_class, _ = SchoolClass.objects.update_or_create(
                name=name, defaults={'level': level, 'fee_band': bands[band_name], 'order': order},
            )
            for section_name in sections:
                Section.objects.get_or_create(school_class=school_class, name=section_name)
        self.stdout.write(self.style.SUCCESS(f'Classes: {len(CLASS_LIST)} with sections'))

        subject_count = 0
        for level, subjects in SUBJECTS_BY_LEVEL.items():
            for subject_name in subjects:
                Subject.objects.get_or_create(name=subject_name, level=level)
                subject_count += 1
        self.stdout.write(self.style.SUCCESS(f'Subjects: {subject_count} rows across {len(SUBJECTS_BY_LEVEL)} levels'))
