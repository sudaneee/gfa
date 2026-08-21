from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from admissions.models import Application, ApplicationStatusLog
from communication.models import Announcement
from finance.models import FeeStructure, FeeStructureItem, Invoice, InvoiceItem, Payment
from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Term
from students.models import Student


class AdminConsoleAccessTests(TestCase):
    """Every console view is admin_required — proven once here rather than
    repeated per view."""

    def setUp(self):
        self.teacher = User.objects.create_user(username='t1', password='pw', role='teacher')

    def test_non_admin_is_redirected_away_from_the_console(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('admin_console:home'))
        self.assertRedirects(response, reverse('portal:home'))


class GenericCrudTests(TestCase):
    """Announcement stands in for the whole registry — the scaffold is
    generic, so proving it end-to-end on one model proves the mechanism."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

    def test_list_search_and_filter(self):
        Announcement.objects.create(title='Sports Day', content='...', audience='all_parents')
        Announcement.objects.create(title='Staff Meeting', content='...', audience='teachers')

        response = self.client.get(reverse('admin_console:list', args=['announcements']), {'q': 'Sports'})
        self.assertContains(response, 'Sports Day')
        self.assertNotContains(response, 'Staff Meeting')

        response = self.client.get(reverse('admin_console:list', args=['announcements']), {'audience': 'teachers'})
        self.assertContains(response, 'Staff Meeting')
        self.assertNotContains(response, 'Sports Day')

    def test_create_edit_delete_round_trip(self):
        response = self.client.post(reverse('admin_console:create', args=['announcements']), {
            'title': 'New Term Begins', 'content': 'School resumes Monday.',
            'audience': 'all_parents', 'is_published': 'on',
        })
        self.assertRedirects(response, reverse('admin_console:list', args=['announcements']))
        announcement = Announcement.objects.get(title='New Term Begins')

        response = self.client.post(reverse('admin_console:edit', args=['announcements', announcement.pk]), {
            'title': 'New Term Begins (Updated)', 'content': 'School resumes Tuesday.',
            'audience': 'students', 'is_published': 'on',
        })
        self.assertRedirects(response, reverse('admin_console:list', args=['announcements']))
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, 'New Term Begins (Updated)')
        self.assertEqual(announcement.audience, 'students')

        response = self.client.post(reverse('admin_console:delete', args=['announcements', announcement.pk]))
        self.assertRedirects(response, reverse('admin_console:list', args=['announcements']))
        self.assertFalse(Announcement.objects.filter(pk=announcement.pk).exists())

    def test_unknown_slug_404s(self):
        response = self.client.get(reverse('admin_console:list', args=['not-a-real-model']))
        self.assertEqual(response.status_code, 404)


class ApplicationConsoleTests(TestCase):
    """Status changes must go through Application.set_status() — a status
    log row proves the console isn't just flipping the field directly."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)
        self.application = Application.objects.create(
            first_name='Test', last_name='Applicant', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='Parent', relationship='Father',
            phone='08000000000', email='applicant@example.com', address='Address',
            applying_for='primary', is_submitted=True,
        )

    def test_status_change_writes_a_status_log(self):
        response = self.client.post(reverse('admin_console:application_detail', args=[self.application.pk]), {
            'status': 'shortlisted',
        })
        self.assertRedirects(response, reverse('admin_console:application_detail', args=[self.application.pk]))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'shortlisted')
        self.assertTrue(ApplicationStatusLog.objects.filter(application=self.application, stage='shortlisted').exists())


class PaymentConsoleTests(TestCase):
    """Mark Received must produce the same result as the admin's own
    save_model — proven by checking both the payment stamp and the
    invoice status rollup."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        fee_band = FeeBand.objects.create(name='Primary')
        school_class = SchoolClass.objects.create(name='Primary 3', level='Primary', order=1, fee_band=fee_band)
        section = Section.objects.create(school_class=school_class, name='A')
        structure = FeeStructure.objects.create(session=session, fee_band=fee_band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=structure, category='Tuition', amount=50000)
        student = Student.objects.create(first_name='Pay', last_name='Test', gender='Male', school_class=school_class, section=section)
        self.invoice = Invoice.objects.create(student=student, term=self.term, fee_structure=structure)
        InvoiceItem.objects.create(invoice=self.invoice, category='Tuition', amount=50000)
        self.payment = Payment.objects.create(invoice=self.invoice, amount=50000, gateway='manual', status='pending')

    def test_mark_received_stamps_the_payment_and_syncs_the_invoice(self):
        response = self.client.post(reverse('admin_console:payment_mark_received'), {'pk': self.payment.pk, 'qs': ''})
        self.assertRedirects(response, reverse('admin_console:payments_list'))

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertIsNotNone(self.payment.paid_at)
        self.assertTrue(self.payment.receipt_number)
        self.assertEqual(self.invoice.status, 'paid')


class FeeStructureConsoleTests(TestCase):
    """The one deliberately non-generic financial-config model — proves
    the console respects the same is_locked guarantee finance/admin.py
    already enforces, instead of silently regressing it."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)
        self.session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.fee_band = FeeBand.objects.create(name='Primary')

    def _formset_data(self, **overrides):
        data = {
            'session': self.session.pk, 'fee_band': self.fee_band.pk, 'student_category': 'new',
            'items-TOTAL_FORMS': '1', 'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '1000',
            'items-0-category': 'Tuition', 'items-0-amount': '50000',
        }
        data.update(overrides)
        return data

    def test_create_with_items(self):
        response = self.client.post(reverse('admin_console:fee_structure_create'), self._formset_data())
        self.assertRedirects(response, reverse('admin_console:fee_structures_list'))
        structure = FeeStructure.objects.get(session=self.session, fee_band=self.fee_band, student_category='new')
        self.assertEqual(structure.items.count(), 1)
        self.assertEqual(structure.total_amount, 50000)

    def test_locked_structure_cannot_be_edited_or_deleted(self):
        structure = FeeStructure.objects.create(session=self.session, fee_band=self.fee_band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=structure, category='Tuition', amount=50000)
        structure.lock()

        response = self.client.post(reverse('admin_console:fee_structure_edit', args=[structure.pk]), self._formset_data())
        self.assertRedirects(response, reverse('admin_console:fee_structures_list'))
        structure.refresh_from_db()
        self.assertEqual(structure.items.count(), 1)  # unchanged — edit was blocked before touching anything

        response = self.client.post(reverse('admin_console:fee_structure_delete', args=[structure.pk]))
        self.assertRedirects(response, reverse('admin_console:fee_structures_list'))
        self.assertTrue(FeeStructure.objects.filter(pk=structure.pk).exists())  # still there — delete was blocked

    def test_unlocked_structure_can_be_deleted(self):
        structure = FeeStructure.objects.create(session=self.session, fee_band=self.fee_band, student_category='new')
        response = self.client.post(reverse('admin_console:fee_structure_delete', args=[structure.pk]))
        self.assertRedirects(response, reverse('admin_console:fee_structures_list'))
        self.assertFalse(FeeStructure.objects.filter(pk=structure.pk).exists())


class UserCreationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

    def test_create_user_with_hashed_password(self):
        response = self.client.post(reverse('accounts:user_create'), {
            'username': 'newteacher', 'first_name': 'New', 'last_name': 'Teacher',
            'email': 'newteacher@example.com', 'role': 'teacher', 'is_active': 'on',
            'password1': 'a-strong-password-1', 'password2': 'a-strong-password-1',
        })
        self.assertRedirects(response, reverse('accounts:user_list'))
        user = User.objects.get(username='newteacher')
        self.assertEqual(user.role, 'teacher')
        self.assertTrue(user.check_password('a-strong-password-1'))

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(reverse('accounts:user_create'), {
            'username': 'baduser', 'first_name': 'Bad', 'last_name': 'User',
            'email': 'bad@example.com', 'role': 'teacher', 'is_active': 'on',
            'password1': 'a-strong-password-1', 'password2': 'a-different-one',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())
