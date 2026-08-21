"""
Wipes all demo *records* (students, staff, results, attendance, invoices,
payments, applications, announcements/events, academic structure) and
rebuilds them from scratch via the seed_* commands, in dependency order.

Deliberately leaves untouched:
  - User accounts (the 4 demo logins + any real accounts created since)
  - SchoolSettings (the school's own identity/contact/bank configuration)

This is the backend equivalent of the frontend prototype's "Reset Demo
Data" button in Settings.

Usage: python manage.py reset_demo_data
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Wipe all demo records and reseed a fresh, consistent dataset.'

    def handle(self, *args, **options):
        with transaction.atomic():
            self._wipe()
        self.stdout.write(self.style.SUCCESS('Wiped. Reseeding...'))

        call_command('seed_academics')
        call_command('seed_fee_structures')
        call_command('seed_grade_boundaries')
        call_command('seed_score_components')
        call_command('seed_demo_people')
        call_command('seed_demo_data')

        self.stdout.write(self.style.SUCCESS('Demo data reset complete.'))

    def _wipe(self):
        from admissions.models import Application, ApplicationInvoice, ApplicationPayment, ApplicationStatusLog
        from attendance.models import AttendanceRecord
        from communication.models import Announcement, Event
        from finance.models import FeeStructure, FeeStructureItem, Invoice, InvoiceItem
        from finance.models import Payment as FeePayment
        from results.models import GradeBoundary, Result, ScoreComponent
        from staff.models import Teacher
        from students.models import Guardian, Student
        from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Subject, Term
        from website.models import ContactMessage

        # Children before parents; most FKs cascade, but being explicit keeps
        # this readable and immune to future on_delete changes.
        FeePayment.objects.all().delete()
        InvoiceItem.objects.all().delete()
        Invoice.objects.all().delete()
        FeeStructureItem.objects.all().delete()
        FeeStructure.objects.all().delete()

        ApplicationPayment.objects.all().delete()
        ApplicationInvoice.objects.all().delete()
        ApplicationStatusLog.objects.all().delete()
        Application.objects.all().delete()

        Result.objects.all().delete()
        ScoreComponent.objects.all().delete()
        GradeBoundary.objects.all().delete()
        AttendanceRecord.objects.all().delete()

        Student.objects.all().delete()
        Guardian.objects.all().delete()
        Teacher.objects.all().delete()

        Section.objects.all().delete()
        SchoolClass.objects.all().delete()
        Subject.objects.all().delete()
        Term.objects.all().delete()
        AcademicSession.objects.all().delete()
        FeeBand.objects.all().delete()

        Announcement.objects.all().delete()
        Event.objects.all().delete()
        ContactMessage.objects.all().delete()
