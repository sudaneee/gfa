from django.core.management.base import BaseCommand

from results.models import GradeBoundary

BOUNDARIES = [
    ('A', 70, 100, 5, 'Excellent'),
    ('B', 60, 69, 4, 'Very Good'),
    ('C', 50, 59, 3, 'Good'),
    ('D', 45, 49, 2, 'Fair'),
    ('E', 40, 44, 1, 'Pass'),
    ('F', 0, 39, 0, 'Fail'),
]


class Command(BaseCommand):
    help = 'Seed the default A-F grade boundaries.'

    def handle(self, *args, **options):
        for grade, lo, hi, point, remark in BOUNDARIES:
            GradeBoundary.objects.update_or_create(
                grade=grade, defaults={'min_score': lo, 'max_score': hi, 'point': point, 'remark': remark},
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(BOUNDARIES)} grade boundaries.'))
