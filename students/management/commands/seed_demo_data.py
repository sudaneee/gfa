"""
Populates a realistic bulk demo dataset — students spread across every
class, teachers, guardians, results, attendance history, and fee
invoices/payments — replacing the frontend prototype's assets/js/data.js
generator now that there's a real database.

Assumes seed_academics, seed_fee_structures, seed_grade_boundaries and
seed_demo_people have already run (reset_demo_data runs all of them in
order). Safe to call on its own on top of an empty dataset; running it
twice will create a second batch of students rather than topping up —
use reset_demo_data for a clean slate.

Usage: python manage.py seed_demo_data
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import Section, Term
from attendance.models import AttendanceRecord
from finance.services import InvoiceGenerationError, generate_invoice
from finance.models import Payment
from payments.services import generate_receipt_number
from results.models import GradeBoundary, ScoreComponent
from results.services import save_result_scores
from staff.models import Teacher
from students.models import Guardian, Student

MALE_NAMES = ['Muhammad', 'Ibrahim', 'Abdullahi', 'Yusuf', 'Suleiman', 'Aliyu', 'Emmanuel', 'Chinedu', 'Samuel',
              'David', 'Daniel', 'Joseph', 'Peter', 'Musa', 'Umar', 'Bashir', 'Sani', 'Kabiru', 'Victor', 'Ahmad']
FEMALE_NAMES = ['Aisha', 'Fatima', 'Zainab', 'Hauwa', 'Amina', 'Blessing', 'Grace', 'Mary', 'Ruth', 'Esther',
                'Comfort', 'Faith', 'Chioma', 'Ngozi', 'Halima', 'Rahma', 'Success', 'Precious', 'Deborah', 'Sarah']
SURNAMES = ['Ibrahim', 'Musa', 'Abdullahi', 'Yakubu', 'Suleiman', 'Bello', 'Garba', 'Sani', 'Aliyu', 'Umar',
            'Danjuma', 'Okafor', 'Eze', 'Nwosu', 'Chukwu', 'Okoro', 'Adeyemi', 'Balogun', 'Ojo', 'Afolabi']
OCCUPATIONS = ['Civil Servant', 'Trader', 'Engineer', 'Nurse', 'Teacher', 'Business Owner', 'Banker',
               'Accountant', 'Farmer', 'Driver', 'Tailor', 'Contractor']
DEPARTMENTS = ['Mathematics', 'English Language', 'Sciences', 'Social Studies', 'ICT', 'Early Years', 'Languages']


class Command(BaseCommand):
    help = 'Seed a realistic bulk demo dataset: students, teachers, guardians, results, attendance, fee payments.'

    def handle(self, *args, **options):
        rng = random.Random(42)  # deterministic across runs for reproducible demos
        term = Term.get_current()
        if not term:
            self.stderr.write(self.style.ERROR('No current term — run seed_academics first.'))
            return

        sections = list(Section.objects.select_related('school_class').all())
        if not sections:
            self.stderr.write(self.style.ERROR('No classes/sections — run seed_academics first.'))
            return

        students = self._seed_students_and_guardians(rng, sections)
        self._seed_teachers(rng, sections)
        self._seed_results(rng, students, term)
        self._seed_attendance(rng, students, term)
        self._seed_fees(rng, students, term)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(students)} students across {len(sections)} sections, plus teachers, '
            f'results, attendance and fee invoices for {term}.'
        ))

    def _seed_students_and_guardians(self, rng, sections):
        students = []
        pending_pairing = []  # students awaiting a guardian, paired up 1-2 per household

        for i in range(40):
            gender = 'Male' if i % 2 == 0 else 'Female'
            first = rng.choice(MALE_NAMES if gender == 'Male' else FEMALE_NAMES)
            last = rng.choice(SURNAMES)
            section = sections[i % len(sections)]
            student = Student.objects.create(
                first_name=first, last_name=last, gender=gender,
                school_class=section.school_class, section=section, status='Active',
                admission_date=timezone.localdate(),
            )
            students.append(student)
            pending_pairing.append(student)

        # Group into households of 1-2 children each, matching the frontend's dummy-data pattern.
        i = 0
        household_no = 1
        while i < len(pending_pairing):
            take_two = i + 1 < len(pending_pairing) and household_no % 3 == 0
            kids = pending_pairing[i:i + 2] if take_two else pending_pairing[i:i + 1]
            g_gender = 'Male' if household_no % 2 else 'Female'
            g_first = rng.choice(MALE_NAMES if g_gender == 'Male' else FEMALE_NAMES)
            g_last = rng.choice(SURNAMES)
            guardian = Guardian.objects.create(
                name=f'{g_first} {g_last}', relationship=rng.choice(['Father', 'Mother', 'Guardian']),
                phone=f"081{rng.randint(10000000, 99999999)}", email=f"{g_first.lower()}.{g_last.lower()}{household_no}@example.com",
                address=f"No. {household_no + 3} {rng.choice(['Almara', 'Dalhatu', 'Kuchi', 'Zuma'])} Street, Suleja, Niger State",
                occupation=rng.choice(OCCUPATIONS),
            )
            for kid in kids:
                kid.guardian = guardian
                kid.save(update_fields=['guardian'])
            i += 2 if take_two else 1
            household_no += 1

        return students

    def _seed_teachers(self, rng, sections):
        names = [
            ('Male', 'Yusuf', 'Bello'), ('Female', 'Comfort', 'Nwosu'), ('Male', 'Emmanuel', 'Okoro'),
            ('Female', 'Halima', 'Garba'), ('Male', 'Peter', 'Etim'), ('Female', 'Faith', 'Balogun'),
            ('Male', 'Suleiman', 'Danjuma'), ('Female', 'Ngozi', 'Chukwu'), ('Male', 'Victor', 'Afolabi'),
            ('Female', 'Zainab', 'Sani'),
        ]
        for i, (gender, first, last) in enumerate(names):
            teacher = Teacher.objects.create(
                first_name=first, last_name=last, gender=gender, department=rng.choice(DEPARTMENTS),
                qualification=rng.choice(['B.Sc. Ed.', 'B.A. Ed.', 'NCE', 'B.Ed.', 'M.Ed.']),
                phone=f"080{rng.randint(10000000, 99999999)}", email=f"{first.lower()}.{last.lower()}@gfa.edu.ng",
            )
            teacher.sections.set(rng.sample(sections, k=min(2, len(sections))))

    def _seed_results(self, rng, students, term):
        boundaries = list(GradeBoundary.objects.all())
        if not boundaries:
            self.stderr.write(self.style.WARNING('No grade boundaries — run seed_grade_boundaries first. Skipping results.'))
            return
        components = list(ScoreComponent.objects.order_by('order'))
        if not components:
            self.stderr.write(self.style.WARNING('No score components — run seed_score_components first. Skipping results.'))
            return
        from academics.models import Subject

        count = 0
        for student in students:
            subjects = list(Subject.objects.filter(level=student.school_class.level)[:6])
            for subject in subjects:
                component_values = {c.id: rng.randint(round(c.max_score * 0.5), c.max_score) for c in components}
                exam = rng.randint(35, 70)
                save_result_scores(student, subject, term, None, exam, component_values)
                count += 1
        self.stdout.write(f'  results: {count}')

    def _seed_attendance(self, rng, students, term):
        days = []
        d = timezone.localdate()
        while len(days) < 15:
            if d.weekday() < 5:
                days.append(d)
            d -= timezone.timedelta(days=1)

        count = 0
        for student in students:
            for day in days:
                roll = rng.random()
                status = 'Present' if roll < 0.85 else 'Absent' if roll < 0.95 else 'Late'
                AttendanceRecord.objects.get_or_create(
                    student=student, date=day,
                    defaults={'section': student.section, 'term': term, 'status': status},
                )
                count += 1
        self.stdout.write(f'  attendance: {count}')

    def _seed_fees(self, rng, students, term):
        created, paid_count = 0, 0
        for student in students:
            try:
                invoice = generate_invoice(student, term)
            except InvoiceGenerationError:
                continue
            created += 1
            roll = rng.random()
            if roll < 0.5:  # fully paid
                amount = invoice.balance
            elif roll < 0.75:  # partially paid
                pct = Decimal(rng.randint(30, 70))
                amount = (invoice.balance * pct / Decimal(100)).quantize(Decimal('1'))
            else:  # unpaid
                continue
            if amount <= 0:
                continue
            Payment.objects.create(
                invoice=invoice, amount=amount, gateway=rng.choice(['zainpay', 'manual']), status='success',
                paid_at=timezone.now(), receipt_number=generate_receipt_number(),
            )
            invoice.status = 'paid' if invoice.is_paid else 'partial'
            invoice.save(update_fields=['status'])
            paid_count += 1
        self.stdout.write(f'  invoices: {created} ({paid_count} with a payment recorded)')
