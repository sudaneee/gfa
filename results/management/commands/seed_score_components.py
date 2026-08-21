from django.core.management.base import BaseCommand

from results.models import ScoreComponent

DEFAULTS = [
    ('CA1', 10, 1),
    ('CA2', 10, 2),
    ('CA3', 10, 3),
]


class Command(BaseCommand):
    help = 'Seed the default CA1/CA2/CA3 continuous-assessment components (10 marks each, summing to 30 — matching the exam max of 70 for a 100-mark total).'

    def handle(self, *args, **options):
        for name, max_score, order in DEFAULTS:
            ScoreComponent.objects.update_or_create(
                name=name, defaults={'max_score': max_score, 'order': order},
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(DEFAULTS)} score components.'))
