from decimal import Decimal

from django.test import TestCase

from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Term
from finance.models import FeeStructure, FeeStructureItem, Invoice
from finance.services import InvoiceGenerationError, generate_invoice, generate_invoices_for_term, student_category
from students.models import Student


class FinanceTestBase(TestCase):
    def setUp(self):
        self.session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=self.session, name='first', is_current=True)
        self.band = FeeBand.objects.create(name='Junior Secondary')
        self.school_class = SchoolClass.objects.create(name='JSS 2', level='Secondary', order=10, fee_band=self.band)
        self.section = Section.objects.create(school_class=self.school_class, name='A')

        self.new_structure = FeeStructure.objects.create(session=self.session, fee_band=self.band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=self.new_structure, category='Tuition', amount=25000)
        FeeStructureItem.objects.create(fee_structure=self.new_structure, category='Uniform', amount=9000)
        FeeStructureItem.objects.create(fee_structure=self.new_structure, category='Jacket (optional)', amount=10000, is_optional=True)

        self.continuing_structure = FeeStructure.objects.create(session=self.session, fee_band=self.band, student_category='continuing')
        FeeStructureItem.objects.create(fee_structure=self.continuing_structure, category='Termly Fee', amount=31000)

        self.student = Student.objects.create(
            first_name='Test', last_name='Student', gender='Male', school_class=self.school_class, section=self.section,
        )


class FeeStructureTotalTests(FinanceTestBase):
    def test_total_amount_excludes_optional_items(self):
        self.assertEqual(self.new_structure.total_amount, Decimal('34000'))  # 25000 + 9000, Jacket excluded


class StudentCategoryTests(FinanceTestBase):
    def test_first_ever_invoice_is_new(self):
        self.assertEqual(student_category(self.student), 'new')

    def test_second_term_is_continuing(self):
        generate_invoice(self.student, self.term)
        term2 = Term.objects.create(session=self.session, name='second')
        self.assertEqual(student_category(self.student), 'continuing')


class InvoiceGenerationTests(FinanceTestBase):
    def test_new_student_gets_itemized_invoice_matching_structure(self):
        invoice = generate_invoice(self.student, self.term)
        self.assertEqual(invoice.total, Decimal('34000'))
        self.assertEqual(invoice.items.count(), 2)  # Jacket excluded
        self.assertFalse(invoice.items.filter(category__icontains='Jacket').exists())

    def test_generating_twice_is_idempotent_and_does_not_duplicate(self):
        first = generate_invoice(self.student, self.term)
        second = generate_invoice(self.student, self.term)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Invoice.objects.filter(student=self.student, term=self.term).count(), 1)

    def test_generating_locks_the_fee_structure(self):
        self.assertFalse(self.new_structure.is_locked)
        generate_invoice(self.student, self.term)
        self.new_structure.refresh_from_db()
        self.assertTrue(self.new_structure.is_locked)

    def test_missing_fee_band_raises(self):
        unbanded_class = SchoolClass.objects.create(name='SSS 1', level='Secondary', order=20)  # no fee_band
        section = Section.objects.create(school_class=unbanded_class, name='A')
        student = Student.objects.create(
            first_name='No', last_name='Band', gender='Male', school_class=unbanded_class, section=section,
        )
        with self.assertRaises(InvoiceGenerationError):
            generate_invoice(student, self.term)

    def test_amount_is_frozen_after_fee_structure_changes(self):
        """The core requirement: editing FeeStructure after invoices exist
        must never alter an already-generated invoice's amount."""
        invoice = generate_invoice(self.student, self.term)
        original_total = invoice.total
        self.assertEqual(original_total, Decimal('34000'))

        # A new session's structure is created (the "raise fees" scenario) —
        # the old structure/invoice must be untouched.
        new_session = AcademicSession.objects.create(name='2026/2027')
        new_term = Term.objects.create(session=new_session, name='first')
        newer_structure = FeeStructure.objects.create(session=new_session, fee_band=self.band, student_category='continuing')
        FeeStructureItem.objects.create(fee_structure=newer_structure, category='Termly Fee', amount=50000)

        invoice.refresh_from_db()
        self.assertEqual(invoice.total, original_total)


class BatchInvoiceGenerationTests(FinanceTestBase):
    def test_batch_generation_skips_existing_and_reports_summary(self):
        generate_invoice(self.student, self.term)  # pre-existing
        student2 = Student.objects.create(
            first_name='Second', last_name='Student', gender='Female', school_class=self.school_class, section=self.section,
        )
        summary = generate_invoices_for_term(self.term, students=Student.objects.all())
        self.assertEqual(summary['created'], 1)
        self.assertEqual(summary['skipped'], 1)
        self.assertEqual(summary['errors'], [])
