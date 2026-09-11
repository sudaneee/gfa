from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from admissions.models import Application, ApplicationInvoice, ApplicationPayment, ApplicationStatusLog
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


class ApplicationPaymentEditTests(TestCase):
    """Same manual-only editing rule as termly fee payments, applied to
    application-fee payments — and shown on the application's own detail
    page rather than a separate list, since that's the only place they're
    ever surfaced."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)
        self.application = Application.objects.create(
            first_name='Test', last_name='Applicant', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='Parent', relationship='Father',
            phone='08000000000', email='applicant@example.com', address='Address', applying_for='Creche',
        )
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=2000)
        self.manual_payment = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=2000, gateway='manual', status='success',
        )

    def test_manual_payment_shows_on_the_application_detail_page(self):
        response = self.client.get(reverse('admin_console:application_detail', args=[self.application.pk]))
        self.assertContains(response, self.manual_payment.reference)
        self.assertContains(response, reverse('admin_console:application_payment_edit', args=[self.manual_payment.pk]))

    def test_manual_payment_can_be_edited(self):
        response = self.client.post(reverse('admin_console:application_payment_edit', args=[self.manual_payment.pk]), {
            'amount': '2000', 'status': 'success', 'notes': 'Confirmed via bank statement.',
        })
        self.assertRedirects(response, reverse('admin_console:application_detail', args=[self.application.pk]))

        self.manual_payment.refresh_from_db()
        self.assertEqual(self.manual_payment.notes, 'Confirmed via bank statement.')
        self.assertEqual(self.manual_payment.updated_by, self.admin)

    def test_zainpay_payment_cannot_be_edited(self):
        zainpay_payment = ApplicationPayment.objects.create(invoice=self.invoice, amount=2000, gateway='zainpay', status='success')
        response = self.client.get(reverse('admin_console:application_payment_edit', args=[zainpay_payment.pk]))
        self.assertRedirects(response, reverse('admin_console:application_detail', args=[self.application.pk]))


class ApplicationsListVisibilityTests(TestCase):
    """The admin complained he wasn't seeing all applications — root cause
    was the list only ever showed is_submitted=True, silently hiding
    anyone who'd paid the fee but hadn't clicked through the rest of the
    form yet. Paid-but-unsubmitted is now shown too; blank/unpaid
    abandoned drafts (not really "an application" yet) stay hidden."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

        self.submitted = Application.objects.create(
            first_name='Submitted', last_name='Kid', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='Parent A', relationship='Father',
            phone='08000000001', email='a@example.com', address='Address', applying_for='Creche',
            is_submitted=True,
        )
        self.paid_unsubmitted = Application.objects.create(
            first_name='', last_name='', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', is_submitted=False,
        )
        ApplicationInvoice.objects.create(application=self.paid_unsubmitted, amount=2000, status='paid')
        self.unpaid_draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', is_submitted=False,
        )

    def test_paid_but_unsubmitted_is_now_visible(self):
        response = self.client.get(reverse('admin_console:applications_list'))
        self.assertContains(response, self.submitted.application_number)
        self.assertContains(response, self.paid_unsubmitted.application_number)

    def test_blank_unpaid_draft_stays_hidden(self):
        response = self.client.get(reverse('admin_console:applications_list'))
        self.assertNotContains(response, self.unpaid_draft.application_number)

    def test_stage_filter_submitted_excludes_paid_in_progress(self):
        response = self.client.get(reverse('admin_console:applications_list'), {'stage': 'submitted'})
        self.assertContains(response, self.submitted.application_number)
        self.assertNotContains(response, self.paid_unsubmitted.application_number)

    def test_stage_filter_in_progress_excludes_submitted(self):
        response = self.client.get(reverse('admin_console:applications_list'), {'stage': 'in_progress'})
        self.assertContains(response, self.paid_unsubmitted.application_number)
        self.assertNotContains(response, self.submitted.application_number)


class ApplicationEnrollTests(TestCase):
    """The "Enroll as Student" action that closes the loop Student.application
    was always meant for — creates the Student, links/reuses a Guardian, and
    generates the term's invoice, all from one admitted Application."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        fee_band = FeeBand.objects.create(name='Primary')
        school_class = SchoolClass.objects.create(name='Primary 3', level='Primary', order=1, fee_band=fee_band)
        self.section = Section.objects.create(school_class=school_class, name='A')
        structure = FeeStructure.objects.create(session=session, fee_band=fee_band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=structure, category='Tuition', amount=50000)

        self.application = Application.objects.create(
            first_name='Test', last_name='Applicant', date_of_birth='2015-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='Test Parent', relationship='Father',
            phone='08011112222', email='parent@example.com', address='Test address',
            applying_for='Primary 3', is_submitted=True, status='admitted',
        )

    def test_enroll_requires_admitted_status(self):
        self.application.status = 'shortlisted'
        self.application.save(update_fields=['status'])

        response = self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk,
        })
        self.assertRedirects(response, reverse('admin_console:application_detail', args=[self.application.pk]))
        self.assertFalse(Student.objects.exists())

    def test_enroll_creates_student_guardian_login_and_invoice(self):
        response = self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk, 'create_login': 'on',
        })
        student = Student.objects.get(application=self.application)
        self.assertRedirects(response, reverse('admin_console:edit', args=['students', student.pk]))

        self.assertEqual(student.first_name, 'Test')
        self.assertEqual(student.section, self.section)
        self.assertEqual(student.school_class, self.section.school_class)
        self.assertIsNotNone(student.guardian)
        self.assertEqual(student.guardian.name, 'Test Parent')
        self.assertTrue(student.guardian.user_id)
        self.assertEqual(student.guardian.user.role, 'parent')

        self.assertTrue(Invoice.objects.filter(student=student, term=self.term).exists())

    def test_enroll_without_login_checkbox_creates_no_user(self):
        self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk,
        })
        student = Student.objects.get(application=self.application)
        self.assertIsNotNone(student.guardian)
        self.assertFalse(student.guardian.user_id)

    def test_sibling_reuses_existing_guardian_instead_of_duplicating(self):
        from students.models import Guardian

        existing_guardian = Guardian.objects.create(
            name='Test Parent', relationship='Father', phone='08011112222', email='parent@example.com',
        )
        self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk, 'create_login': 'on',
        })

        student = Student.objects.get(application=self.application)
        self.assertEqual(student.guardian_id, existing_guardian.pk)
        self.assertEqual(Guardian.objects.count(), 1)  # no duplicate created

    def test_cannot_enroll_the_same_application_twice(self):
        self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk,
        })
        first_student = Student.objects.get(application=self.application)

        response = self.client.post(reverse('admin_console:application_enroll', args=[self.application.pk]), {
            'section': self.section.pk,
        })
        self.assertRedirects(response, reverse('admin_console:edit', args=['students', first_student.pk]))
        self.assertEqual(Student.objects.filter(application=self.application).count(), 1)


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


class FeePaymentEditTests(TestCase):
    """Editing is only ever offered for gateway='manual' — a ZainPay
    payment is a real transaction, not something to retype by hand. Every
    edit is attributed (updated_by/updated_at), and the invoice is kept in
    sync with whatever the edit changes."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        fee_band = FeeBand.objects.create(name='Primary')
        school_class = SchoolClass.objects.create(name='Primary 3', level='Primary', order=1, fee_band=fee_band)
        section = Section.objects.create(school_class=school_class, name='A')
        structure = FeeStructure.objects.create(session=session, fee_band=fee_band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=structure, category='Tuition', amount=79000)
        student = Student.objects.create(first_name='Pay', last_name='Test', gender='Male', school_class=school_class, section=section)
        self.invoice = Invoice.objects.create(student=student, term=self.term, fee_structure=structure)
        InvoiceItem.objects.create(invoice=self.invoice, category='Tuition', amount=79000)
        self.manual_payment = Payment.objects.create(
            invoice=self.invoice, amount=79000, gateway='manual', status='success', paid_at=None,
        )

    def test_manual_payment_can_be_edited(self):
        response = self.client.post(reverse('admin_console:fee_payment_edit', args=[self.manual_payment.pk]), {
            'amount': '40000', 'status': 'success', 'notes': 'Corrected — was double-recorded.',
        })
        self.assertRedirects(response, reverse('admin_console:payments_list'))

        self.manual_payment.refresh_from_db()
        self.assertEqual(self.manual_payment.amount, 40000)
        self.assertEqual(self.manual_payment.notes, 'Corrected — was double-recorded.')
        self.assertEqual(self.manual_payment.updated_by, self.admin)
        self.assertIsNotNone(self.manual_payment.updated_at)

    def test_zainpay_payment_cannot_be_edited(self):
        zainpay_payment = Payment.objects.create(invoice=self.invoice, amount=79000, gateway='zainpay', status='success')

        response = self.client.get(reverse('admin_console:fee_payment_edit', args=[zainpay_payment.pk]))
        self.assertRedirects(response, reverse('admin_console:payments_list'))

        response = self.client.post(reverse('admin_console:fee_payment_edit', args=[zainpay_payment.pk]), {
            'amount': '1', 'status': 'success', 'notes': '',
        })
        self.assertRedirects(response, reverse('admin_console:payments_list'))
        zainpay_payment.refresh_from_db()
        self.assertEqual(zainpay_payment.amount, 79000)  # untouched

    def test_editing_status_to_pending_resyncs_the_invoice(self):
        self.client.post(reverse('admin_console:fee_payment_edit', args=[self.manual_payment.pk]), {
            'amount': '79000', 'status': 'pending', 'notes': 'Was recorded in error.',
        })

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unpaid')

    def test_flipping_status_to_success_stamps_the_success_fields(self):
        self.manual_payment.status = 'pending'
        self.manual_payment.save(update_fields=['status'])

        self.client.post(reverse('admin_console:fee_payment_edit', args=[self.manual_payment.pk]), {
            'amount': '79000', 'status': 'success', 'notes': '',
        })

        self.manual_payment.refresh_from_db()
        self.assertEqual(self.manual_payment.status, 'success')
        self.assertIsNotNone(self.manual_payment.paid_at)
        self.assertTrue(self.manual_payment.receipt_number)


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


class ManualPaymentRegistrationTests(TestCase):
    """The bridge for a parent who paid by bank transfer instead of
    ZainPay — admin creates their account and activates payment in one
    step, reusing the exact same mark_payment_success everything else uses."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

    def _post(self, **overrides):
        data = {
            'full_name': 'Manual Parent', 'email': 'manual.parent@example.com', 'phone': '08033334444',
            'username': 'manualparent', 'password': 'a-strong-password-1', 'amount': '2000',
        }
        data.update(overrides)
        return self.client.post(reverse('admin_console:manual_payment_registration'), data)

    def test_toggle_off_blocks_access(self):
        from website.models import SchoolSettings

        school = SchoolSettings.get_solo()
        school.manual_payment_registration_enabled = False
        school.save()

        response = self.client.get(reverse('admin_console:manual_payment_registration'))
        self.assertRedirects(response, reverse('admin_console:home'))

    def test_creates_account_and_activates_payment_for_a_fresh_application(self):
        from admissions.models import Application
        from students.models import Guardian

        response = self._post()
        self.assertRedirects(response, reverse('admin_console:applications_list'))

        user = User.objects.get(username='manualparent')
        self.assertEqual(user.role, 'parent')
        self.assertTrue(user.check_password('a-strong-password-1'))

        guardian = Guardian.objects.get(user=user)
        self.assertEqual(guardian.phone, '08033334444')

        application = Application.objects.get(created_by=user)
        invoice = application.invoice
        self.assertTrue(invoice.is_paid)
        payment = invoice.payments.get()
        self.assertEqual(payment.status, 'success')
        self.assertEqual(payment.gateway, 'manual')
        self.assertEqual(payment.created_by, self.admin)

    def test_links_and_activates_an_existing_unclaimed_draft(self):
        from admissions.models import Application

        draft = Application.objects.create(
            first_name='Existing', last_name='Draft', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='', relationship='Father',
            phone='08033334444', email='manual.parent@example.com', address='', applying_for='Creche',
        )
        self._post()

        draft.refresh_from_db()
        self.assertIsNotNone(draft.created_by)
        self.assertEqual(draft.created_by.username, 'manualparent')
        self.assertTrue(draft.invoice.is_paid)

    def test_multiple_unclaimed_drafts_requires_disambiguation(self):
        from admissions.models import Application

        first = Application.objects.create(
            first_name='Kid', last_name='One', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='', relationship='Father',
            phone='08033334444', email='manual.parent@example.com', address='', applying_for='Creche',
        )
        second = Application.objects.create(
            first_name='Kid', last_name='Two', date_of_birth='2017-01-01', gender='Female',
            state_of_origin='Niger', lga='Suleja', parent_name='', relationship='Father',
            phone='08033334444', email='manual.parent@example.com', address='', applying_for='Creche',
        )

        response = self._post()
        self.assertEqual(response.status_code, 200)  # re-rendered, not processed
        self.assertContains(response, 'Kid One')
        self.assertContains(response, 'Kid Two')
        self.assertFalse(User.objects.filter(username='manualparent').exists())

        # Now resubmit having picked one.
        self._post(application_id=str(second.pk))
        second.refresh_from_db()
        first.refresh_from_db()
        self.assertIsNotNone(second.created_by)
        self.assertIsNone(first.created_by)  # untouched

    def test_existing_account_is_not_duplicated(self):
        User.objects.create_user(username='alreadyhasone', email='manual.parent@example.com', password='pw', role='parent')
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertFalse(User.objects.filter(username='manualparent').exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username='manualparent', email='someone@example.com', password='pw', role='teacher')
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')


class ManualFeePaymentRegistrationTests(TestCase):
    """Same bridge as ManualPaymentRegistrationTests, for termly school
    fees — no account to create here, an enrolled student's parent
    already has one; this just finds/generates the invoice and records
    the payment against it."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        fee_band = FeeBand.objects.create(name='Primary')
        school_class = SchoolClass.objects.create(name='Primary 3', level='Primary', order=1, fee_band=fee_band)
        section = Section.objects.create(school_class=school_class, name='A')
        self.structure = FeeStructure.objects.create(session=session, fee_band=fee_band, student_category='new')
        FeeStructureItem.objects.create(fee_structure=self.structure, category='Tuition', amount=50000)
        self.student = Student.objects.create(
            first_name='Fee', last_name='Payer', gender='Male', school_class=school_class,
            section=section, admission_number='GFA/2025/999',
        )

    def _post(self, **overrides):
        data = {
            'admission_number': self.student.admission_number, 'term': self.term.pk,
            'amount': '50000', 'notes': 'Paid into Jaiz Bank, confirmed by the bursar.',
        }
        data.update(overrides)
        return self.client.post(reverse('admin_console:manual_fee_payment_registration'), data)

    def test_toggle_off_blocks_access(self):
        from website.models import SchoolSettings

        school = SchoolSettings.get_solo()
        school.manual_payment_registration_enabled = False
        school.save()

        response = self.client.get(reverse('admin_console:manual_fee_payment_registration'))
        self.assertRedirects(response, reverse('admin_console:home'))

    def test_records_payment_against_an_existing_invoice(self):
        invoice = Invoice.objects.create(student=self.student, term=self.term, fee_structure=self.structure)
        InvoiceItem.objects.create(invoice=invoice, category='Tuition', amount=50000)

        response = self._post(amount='30000')
        self.assertRedirects(response, reverse('admin_console:invoices_list'))

        invoice.refresh_from_db()
        payment = invoice.payments.get()
        self.assertEqual(payment.gateway, 'manual')
        self.assertEqual(payment.status, 'success')
        self.assertEqual(payment.amount, 30000)
        self.assertEqual(payment.notes, 'Paid into Jaiz Bank, confirmed by the bursar.')
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(invoice.status, 'partial')
        self.assertEqual(payment.created_by, self.admin)

    def test_full_payment_marks_the_invoice_paid(self):
        invoice = Invoice.objects.create(student=self.student, term=self.term, fee_structure=self.structure)
        InvoiceItem.objects.create(invoice=invoice, category='Tuition', amount=50000)

        self._post(amount='50000')

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')

    def test_generates_the_invoice_when_none_exists_yet(self):
        self.assertFalse(Invoice.objects.filter(student=self.student, term=self.term).exists())

        response = self._post()
        self.assertRedirects(response, reverse('admin_console:invoices_list'))

        invoice = Invoice.objects.get(student=self.student, term=self.term)
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(invoice.payments.get().amount, 50000)

    def test_unknown_admission_number_is_rejected(self):
        response = self._post(admission_number='DOES-NOT-EXIST')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No student found')

    def test_missing_fee_structure_is_reported_without_a_crash(self):
        # No FeeStructure for this student's class/category in this term —
        # generate_invoice can't build one, and the form should say so
        # rather than 500.
        unstructured_band = FeeBand.objects.create(name='Nursery')
        unstructured_class = SchoolClass.objects.create(name='Nursery 1', level='Nursery', order=1, fee_band=unstructured_band)
        student = Student.objects.create(
            first_name='No', last_name='Structure', gender='Female', school_class=unstructured_class,
            admission_number='GFA/2025/998',
        )
        response = self._post(admission_number=student.admission_number)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No fee structure')
        self.assertFalse(Invoice.objects.filter(student=student).exists())


class TeacherCreateTests(TestCase):
    """One save creates both the Teacher profile and their login — the
    generic Teachers registry entry has no field for Teacher.user at all,
    so this dedicated flow is the only way to create a teacher who can
    actually log in, without a separate trip to Users & Roles."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)

    def _post(self, **overrides):
        data = {
            'first_name': 'Grace', 'last_name': 'Adeyemi', 'gender': 'Female',
            'department': 'Primary', 'qualification': 'B.Ed', 'phone': '08011112222',
            'email': 'grace.adeyemi@example.com', 'employment_date': '2024-01-01', 'status': 'Active',
            'username': 'gadeyemi', 'password': 'a-strong-password-1',
            # A checkbox absent from POST data means unchecked, same as a browser —
            # tests that want the "skipped" behaviour don't need to override this.
            'send_login_email': 'on',
        }
        data.update(overrides)
        return self.client.post(reverse('admin_console:teacher_create'), data)

    def test_teachers_list_add_button_points_at_the_dedicated_page(self):
        response = self.client.get(reverse('admin_console:list', args=['teachers']))
        self.assertContains(response, reverse('admin_console:teacher_create'))

    def test_generic_create_url_resolves_to_the_dedicated_page(self):
        # 'teachers/add/' is registered explicitly ahead of the generic
        # '<slug:slug>/add/' catch-all, so it's routed straight to
        # teacher_create — entry.create_url_name's redirect inside
        # generic_create is a fallback for slugs without that explicit
        # override, and is unreachable for 'teachers' specifically.
        response = self.client.get(reverse('admin_console:create', args=['teachers']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Teacher &amp; Login')

    def test_creates_teacher_with_working_login(self):
        from staff.models import Teacher

        response = self._post()
        self.assertRedirects(response, reverse('admin_console:list', args=['teachers']))

        teacher = Teacher.objects.get(first_name='Grace', last_name='Adeyemi')
        self.assertIsNotNone(teacher.user)
        self.assertEqual(teacher.user.role, 'teacher')
        self.assertTrue(teacher.user.check_password('a-strong-password-1'))

        self.client.logout()
        self.assertTrue(self.client.login(username='gadeyemi', password='a-strong-password-1'))

    def test_login_details_are_emailed_by_default(self):
        from django.core import mail

        self._post()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('grace.adeyemi@example.com', mail.outbox[0].to)
        self.assertIn('gadeyemi', mail.outbox[0].body)

    def test_send_login_email_can_be_skipped(self):
        from django.core import mail

        self._post(send_login_email='')
        self.assertEqual(len(mail.outbox), 0)

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username='gadeyemi', email='someone.else@example.com', password='pw', role='teacher')
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username='existing', email='grace.adeyemi@example.com', password='pw', role='teacher')
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
