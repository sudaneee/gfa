"""
Creates the four demo accounts already advertised on the frontend prototype's
login page (assets/js/storage.js DemoAccounts) and login.html, so the exact
same credentials work against the real backend.

Usage: python manage.py seed_demo_users
"""

from django.core.management.base import BaseCommand

from accounts.models import User

DEMO_USERS = [
    {
        'username': 'admin', 'email': 'admin@gfa.edu.ng', 'password': 'admin123',
        'first_name': 'School', 'last_name': 'Administrator', 'role': User.Role.ADMIN,
        'is_staff': True, 'is_superuser': True,
    },
    {
        'username': 'teacher', 'email': 'teacher@gfa.edu.ng', 'password': 'teacher123',
        'first_name': 'Grace', 'last_name': 'Adeyemi', 'role': User.Role.TEACHER,
    },
    {
        'username': 'parent', 'email': 'parent@gfa.edu.ng', 'password': 'parent123',
        'first_name': 'Ibrahim', 'last_name': 'Musa', 'role': User.Role.PARENT,
    },
    {
        'username': 'student', 'email': 'student@gfa.edu.ng', 'password': 'student123',
        'first_name': 'Muhammad', 'last_name': 'Ibrahim', 'role': User.Role.STUDENT,
    },
]


class Command(BaseCommand):
    help = 'Create/update the four demo accounts (admin/teacher/parent/student@gfa.edu.ng).'

    def handle(self, *args, **options):
        for source in DEMO_USERS:
            # Copy before popping — DEMO_USERS is a module-level list, so
            # mutating the shared dicts directly would break a second call
            # to this command within the same process (tests, or
            # reset_demo_data re-invoking it later in a long-lived worker).
            data = dict(source)
            password = data.pop('password')
            user, created = User.objects.update_or_create(
                username=data['username'], defaults=data,
            )
            user.set_password(password)
            user.save()
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f"{action}: {user.email} ({user.get_role_display()})"))
