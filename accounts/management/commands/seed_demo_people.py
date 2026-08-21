"""
Links the four demo accounts to real domain records, so logging in as
teacher@gfa.edu.ng / parent@gfa.edu.ng / student@gfa.edu.ng lands on
coherent, cross-referenced data — same story as the frontend prototype's
dummy data (Grace Adeyemi teaches JSS2/Primary5; Ibrahim Musa is parent to
Aisha Ibrahim (Primary5) and Muhammad Ibrahim (JSS2)).

Run seed_demo_users and seed_academics first.
Usage: python manage.py seed_demo_people
"""

from django.core.management.base import BaseCommand, CommandError

from academics.models import Section, Subject
from accounts.models import User
from staff.models import Teacher
from students.models import Guardian, Student


class Command(BaseCommand):
    help = 'Link demo accounts to real Teacher/Guardian/Student records.'

    def handle(self, *args, **options):
        try:
            teacher_user = User.objects.get(email='teacher@gfa.edu.ng')
            parent_user = User.objects.get(email='parent@gfa.edu.ng')
            student_user = User.objects.get(email='student@gfa.edu.ng')
        except User.DoesNotExist:
            raise CommandError('Demo users not found — run `python manage.py seed_demo_users` first.')

        try:
            primary5a = Section.objects.get(school_class__name='Primary 5', name='A')
            jss2a = Section.objects.get(school_class__name='JSS 2', name='A')
            jss2b = Section.objects.get(school_class__name='JSS 2', name='B')
        except Section.DoesNotExist:
            raise CommandError('Classes/sections not found — run `python manage.py seed_academics` first.')

        guardian, _ = Guardian.objects.update_or_create(
            user=parent_user,
            defaults=dict(name='Ibrahim Musa', relationship='Father', phone='08117436216',
                          email=parent_user.email, address='No. 12 Almara Street, Suleja, Niger State',
                          occupation='Civil Servant'),
        )

        Student.objects.update_or_create(
            first_name='Aisha', last_name='Ibrahim',
            defaults=dict(gender='Female', school_class=primary5a.school_class, section=primary5a, guardian=guardian),
        )
        Student.objects.update_or_create(
            first_name='Muhammad', last_name='Ibrahim', user=student_user,
            defaults=dict(gender='Male', school_class=jss2a.school_class, section=jss2a, guardian=guardian),
        )

        teacher, _ = Teacher.objects.update_or_create(
            user=teacher_user,
            defaults=dict(first_name='Grace', last_name='Adeyemi', gender='Female', department='Mathematics',
                          qualification='B.Sc. Ed. Mathematics', phone='08102969721', email=teacher_user.email),
        )
        math_subjects = Subject.objects.filter(name__in=['Mathematics', 'Basic Science'])
        teacher.subjects.set(math_subjects)
        teacher.sections.set([jss2a, jss2b, primary5a])

        self.stdout.write(self.style.SUCCESS(
            'Linked: Grace Adeyemi (teacher), Ibrahim Musa (parent) with Aisha & Muhammad Ibrahim (student).'
        ))
