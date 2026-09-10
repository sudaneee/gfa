import re
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from admissions.models import Application, ApplicationInvoice, ApplicationPayment, generate_application_number
from students.models import Guardian
from website.models import SchoolSettings


def _make_parent(email='parent@example.com', phone='08000000000', name='Test Parent', with_guardian=True):
    """A logged-in-ready parent account — with a linked Guardian by default,
    since that's what a real signup produces and what _get_draft pre-fills
    a fresh application from."""
    user = User.objects.create_user(username=email, email=email, password='pw', role='parent')
    if with_guardian:
        Guardian.objects.create(name=name, phone=phone, email=email, user=user)
    return user


class ApplicationNumberTests(TestCase):
    def test_format_and_sequential_uniqueness(self):
        first = generate_application_number()
        self.assertRegex(first, r'^GFA-\d{4}-\d{6}$')

        Application.objects.create(
            first_name='A', last_name='B', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='P', relationship='Father',
            phone='080', email='a@example.com', address='addr', applying_for='Primary 1',
            application_number=first,
        )
        second = generate_application_number()
        self.assertNotEqual(first, second)
        self.assertTrue(second > first)


class FeeSnapshotTests(TestCase):
    """
    The core requirement from the build plan: changing SchoolSettings.application_fee
    must never alter an invoice that was already generated.
    """

    def _make_submitted_application(self):
        return Application.objects.create(
            first_name='A', last_name='B', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='Niger', lga='Suleja', parent_name='P', relationship='Father',
            phone='080', email='a@example.com', address='addr', applying_for='Primary 1',
            is_submitted=True,
        )

    def test_invoice_amount_is_frozen_at_creation(self):
        school = SchoolSettings.get_solo()
        school.application_fee = Decimal('2000.00')
        school.save()

        application = self._make_submitted_application()
        invoice = ApplicationInvoice.objects.create(application=application, amount=school.application_fee)
        self.assertEqual(invoice.amount, Decimal('2000.00'))

        # The school raises the fee for a later session.
        school.application_fee = Decimal('3500.00')
        school.save()

        invoice.refresh_from_db()
        self.assertEqual(
            invoice.amount, Decimal('2000.00'),
            'Changing SchoolSettings.application_fee must not alter an already-issued invoice.',
        )

        # A brand new invoice, though, picks up the new fee.
        application2 = self._make_submitted_application()
        new_invoice = ApplicationInvoice.objects.create(
            application=application2, amount=SchoolSettings.get_solo().application_fee,
        )
        self.assertEqual(new_invoice.amount, Decimal('3500.00'))


class PaymentGateTests(TestCase):
    """
    Payment is deliberately the first step now — every form step past it
    must refuse to render until the draft's application-fee invoice is paid.
    """

    def _create_draft_via_payment_step(self):
        self.client.force_login(_make_parent())
        self.client.get(reverse('admissions:apply_payment'))
        draft_id = self.client.session['draft_application_id']
        return Application.objects.get(pk=draft_id)

    def _mark_paid(self, draft):
        ApplicationPayment.objects.create(
            invoice=draft.invoice, amount=draft.invoice.amount, status='success', gateway='manual',
        )
        draft.invoice.status = 'paid'
        draft.invoice.save(update_fields=['status'])

    def test_visiting_payment_step_creates_draft_and_snapshots_fee(self):
        school = SchoolSettings.get_solo()
        school.application_fee = Decimal('2000.00')
        school.save()

        draft = self._create_draft_via_payment_step()
        self.assertFalse(draft.is_submitted)
        self.assertEqual(draft.invoice.amount, Decimal('2000.00'))
        self.assertFalse(draft.invoice.is_paid)

    def test_applicant_step_redirects_to_payment_when_unpaid(self):
        self._create_draft_via_payment_step()
        response = self.client.get(reverse('admissions:apply_applicant'))
        self.assertRedirects(response, reverse('admissions:apply_payment'))

    def test_applicant_step_accessible_once_paid(self):
        draft = self._create_draft_via_payment_step()
        self._mark_paid(draft)
        response = self.client.get(reverse('admissions:apply_applicant'))
        self.assertEqual(response.status_code, 200)

    def test_review_step_redirects_to_payment_without_a_draft_in_session(self):
        response = self.client.get(reverse('admissions:apply_review'))
        # Not following further here — where an anonymous, draft-less visit
        # to apply_payment itself ends up (login) is AccountGatedApplicationTests' concern.
        self.assertRedirects(response, reverse('admissions:apply_payment'), fetch_redirect_response=False)


class AccountGatedApplicationTests(TestCase):
    """
    Starting a *new* application requires an account — but an application
    already in progress before this existed (created_by=NULL) must keep
    working with no login required at all, exactly as before.
    """

    def test_logged_out_visitor_is_sent_to_login_to_start_a_new_application(self):
        response = self.client.get(reverse('admissions:apply_payment'))
        self.assertRedirects(response, f"{reverse('admissions:login')}?next={reverse('admissions:apply_payment')}")
        self.assertFalse(Application.objects.exists())  # nothing silently created

    def test_logged_in_parent_gets_a_draft_prefilled_from_their_guardian_profile(self):
        self.client.force_login(_make_parent(email='dad@example.com', phone='08011112222', name='Dad Person'))
        self.client.get(reverse('admissions:apply_payment'))

        draft_id = self.client.session['draft_application_id']
        draft = Application.objects.get(pk=draft_id)
        self.assertEqual(draft.email, 'dad@example.com')
        self.assertEqual(draft.phone, '08011112222')
        self.assertEqual(draft.parent_name, 'Dad Person')
        self.assertIsNotNone(draft.created_by)

    def test_existing_anonymous_session_draft_keeps_working_without_login(self):
        """Simulates an application already in progress before this feature
        existed — created_by is NULL, and the session already points at it."""
        legacy_draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche',
        )
        session = self.client.session
        session['draft_application_id'] = legacy_draft.pk
        session.save()

        response = self.client.get(reverse('admissions:apply_payment'))
        self.assertEqual(response.status_code, 200)  # not bounced to login

    def test_losing_the_session_pointer_resumes_the_existing_draft_instead_of_duplicating(self):
        """The bug this guards against: an applicant logs in again (a new
        device, a cleared cookie jar, or just a fresh browser session) with
        no session pointer — that used to silently mint another blank,
        unpaid Application every single time instead of finding the one
        they already started."""
        parent = _make_parent()
        self.client.force_login(parent)
        self.client.get(reverse('admissions:apply_payment'))
        self.assertEqual(Application.objects.filter(created_by=parent).count(), 1)
        first_draft_id = self.client.session['draft_application_id']

        # A fresh client — same account, no session pointer at all — logging
        # in again from what's effectively a different device/session.
        fresh_client = self.client_class()
        fresh_client.force_login(parent)
        fresh_client.get(reverse('admissions:apply_payment'))

        self.assertEqual(Application.objects.filter(created_by=parent).count(), 1)  # still just one
        self.assertEqual(int(fresh_client.session['draft_application_id']), first_draft_id)

    def test_apply_new_is_the_one_deliberate_way_to_get_a_second_draft(self):
        parent = _make_parent()
        self.client.force_login(parent)
        self.client.get(reverse('admissions:apply_payment'))  # first, implicit draft
        self.assertEqual(Application.objects.filter(created_by=parent).count(), 1)

        response = self.client.get(reverse('admissions:apply_new'))
        self.assertRedirects(response, reverse('admissions:apply_payment'))
        self.assertEqual(Application.objects.filter(created_by=parent).count(), 2)

    def test_apply_new_requires_login(self):
        response = self.client.get(reverse('admissions:apply_new'))
        self.assertRedirects(response, f"{reverse('admissions:login')}?next={reverse('admissions:apply_new')}")


class ApplicantLoginAndDashboardTests(TestCase):
    """The applicant-facing login + dashboard — deliberately separate from
    the School Portal's accounts:login / portal:home."""

    def test_login_page_is_not_the_school_portal_login(self):
        response = self.client.get(reverse('admissions:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admissions/login.html')
        self.assertTemplateNotUsed(response, 'accounts/login.html')

    def test_successful_login_lands_on_the_applications_dashboard_not_the_portal(self):
        _make_parent(email='applicant@example.com')
        response = self.client.post(reverse('admissions:login'), {'email': 'applicant@example.com', 'password': 'pw'})
        self.assertRedirects(response, reverse('admissions:dashboard'))

    def test_login_by_email_or_username_both_work(self):
        user = User.objects.create_user(username='someweirdusername', email='e@example.com', password='pw', role='parent')
        response = self.client.post(reverse('admissions:login'), {'email': 'e@example.com', 'password': 'pw'})
        self.assertRedirects(response, reverse('admissions:dashboard'))
        self.client.logout()
        response = self.client.post(reverse('admissions:login'), {'email': 'someweirdusername', 'password': 'pw'})
        self.assertRedirects(response, reverse('admissions:dashboard'))

    def test_wrong_password_is_rejected(self):
        _make_parent(email='applicant@example.com')
        response = self.client.post(reverse('admissions:login'), {'email': 'applicant@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('admissions:dashboard'))
        self.assertRedirects(response, f"{reverse('admissions:login')}?next={reverse('admissions:dashboard')}")

    def test_dashboard_lists_only_this_accounts_applications(self):
        mine = _make_parent(email='mine@example.com', phone='08011110000')
        other = _make_parent(email='other@example.com', phone='08022220000')
        Application.objects.create(
            first_name='A', last_name='Mine', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', created_by=mine,
        )
        Application.objects.create(
            first_name='B', last_name='Other', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', created_by=other,
        )
        self.client.force_login(mine)
        response = self.client.get(reverse('admissions:dashboard'))
        self.assertContains(response, 'A Mine')
        self.assertNotContains(response, 'B Other')

    def test_signup_redirects_to_the_dashboard_not_the_portal(self):
        response = self.client.post(reverse('accounts:signup'), {
            'full_name': 'New Applicant', 'email': 'newapplicant@example.com', 'phone': '08099998888',
            'password1': 'a-strong-password-1', 'password2': 'a-strong-password-1',
        })
        self.assertRedirects(response, reverse('admissions:dashboard'))


class ApplicationWizardTests(TestCase):
    """End-to-end smoke test of the session-backed multi-step form, payment-gated."""

    def _pay_first(self):
        self.client.force_login(_make_parent())
        self.client.get(reverse('admissions:apply_payment'))
        draft_id = self.client.session['draft_application_id']
        draft = Application.objects.get(pk=draft_id)
        ApplicationPayment.objects.create(
            invoice=draft.invoice, amount=draft.invoice.amount, status='success', gateway='manual',
        )
        draft.invoice.status = 'paid'
        draft.invoice.save(update_fields=['status'])
        return draft

    def test_full_wizard_flow_creates_a_submitted_application_with_invoice(self):
        self._pay_first()

        self.client.post(reverse('admissions:apply_applicant'), {
            'first_name': 'Halima', 'middle_name': '', 'last_name': 'Yakubu',
            'date_of_birth': '2017-03-14', 'gender': 'Female', 'nationality': 'Nigerian',
            'state_of_origin': 'Niger', 'lga': 'Suleja',
        })
        self.client.post(reverse('admissions:apply_guardian'), {
            'parent_name': 'Yakubu Danladi', 'relationship': 'Father', 'phone': '08099998888',
            'email': 'danladi@example.com', 'address': 'No 9 Zuma Street, Suleja', 'occupation': 'Engineer',
        })
        self.client.post(reverse('admissions:apply_academic'), {
            'applying_for': 'Nursery 1', 'previous_school': '', 'previous_class': '',
            'previous_performance': 'First time in school',
        })
        # Skip real file uploads here — DocumentsForm.clean() requires them,
        # so post nothing and confirm the required-document validation holds.
        doc_response = self.client.post(reverse('admissions:apply_documents'), {})
        self.assertEqual(doc_response.status_code, 200)  # re-rendered with errors, not redirected
        self.assertContains(doc_response, 'This document is required.')

    def test_submitting_review_finalizes_application_and_sends_email(self):
        from django.core import mail

        draft = self._pay_first()
        draft.first_name, draft.last_name = 'Halima', 'Yakubu'
        draft.email = 'danladi@example.com'
        draft.parent_name = 'Yakubu Danladi'
        draft.save()

        response = self.client.post(reverse('admissions:apply_review'))
        draft.refresh_from_db()
        self.assertTrue(draft.is_submitted)
        self.assertEqual(draft.status, 'pending')
        self.assertRedirects(response, reverse('admissions:apply_success', args=[draft.application_number]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(draft.application_number, mail.outbox[0].subject)


class ResumeApplicationTests(TestCase):
    """
    The durable, device-independent way back into an in-progress
    application — must not depend on the session/browser that started it.
    """

    def _create_draft(self):
        self.client.force_login(_make_parent())
        self.client.get(reverse('admissions:apply_payment'))
        draft_id = self.client.session['draft_application_id']
        return Application.objects.get(pk=draft_id)

    def test_valid_token_resumes_in_a_fresh_client_with_no_prior_session(self):
        draft = self._create_draft()
        fresh_client = self.client_class()  # simulates a different browser/device entirely
        response = fresh_client.get(
            reverse('admissions:apply_continue', args=[draft.application_number, draft.resume_token]),
        )
        self.assertRedirects(response, reverse('admissions:apply_payment'))
        self.assertEqual(int(fresh_client.session['draft_application_id']), draft.pk)

    def test_resume_link_also_logs_the_fresh_client_in_as_the_owner(self):
        """resume_token is already a private, email-only-delivered secret —
        using it to sign the visitor in too means a forgotten password
        never blocks resuming."""
        draft = self._create_draft()
        fresh_client = self.client_class()
        fresh_client.get(reverse('admissions:apply_continue', args=[draft.application_number, draft.resume_token]))

        response = fresh_client.get(reverse('portal:home'))
        self.assertEqual(response.wsgi_request.user, draft.created_by)

    def test_wrong_token_is_rejected(self):
        draft = self._create_draft()
        response = self.client_class().get(
            reverse('admissions:apply_continue', args=[draft.application_number, 'not-the-real-token']),
        )
        self.assertRedirects(response, reverse('admissions:info'))

    def test_application_number_alone_is_not_a_valid_credential(self):
        """Sequential + public via tracking — must not work without the real token."""
        draft = self._create_draft()
        response = self.client_class().get(
            reverse('admissions:apply_continue', args=[draft.application_number, 'GFA-2026-000101']),
        )
        self.assertRedirects(response, reverse('admissions:info'))

    def test_already_submitted_application_redirects_to_track_instead(self):
        draft = self._create_draft()
        draft.is_submitted = True
        draft.save()
        response = self.client_class().get(
            reverse('admissions:apply_continue', args=[draft.application_number, draft.resume_token]),
        )
        self.assertRedirects(response, reverse('admissions:track'))

    def test_legacy_anonymous_draft_resume_does_not_log_anyone_in(self):
        """created_by=NULL (pre-login-requirement draft) — resume works
        exactly as before, no magic-login side effect since there's no
        account to log in as."""
        legacy_draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche',
        )
        fresh_client = self.client_class()
        response = fresh_client.get(
            reverse('admissions:apply_continue', args=[legacy_draft.application_number, legacy_draft.resume_token]),
        )
        self.assertRedirects(response, reverse('admissions:apply_payment'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_payment_confirmation_email_contains_a_working_resume_link(self):
        from django.core import mail
        from django.test import override_settings

        draft = self._create_draft()
        draft.email = 'parent@example.com'
        draft.phone = '08012345678'
        draft.save()
        payment = ApplicationPayment.objects.create(
            invoice=draft.invoice, amount=draft.invoice.amount, status='pending', reference='GFA-RESUMETEST01',
        )

        with override_settings(SITE_URL='http://testserver'):
            with patch('payments.services.verify_payment') as mock_verify:
                mock_verify.return_value = {
                    'status': 'success', 'amount': draft.invoice.amount,
                    'gateway_reference': 'GFA-RESUMETEST01', 'raw_response': {},
                }
                from payments import services
                services.process_payment(payment)

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(f'/admissions/apply/continue/{draft.application_number}/{draft.resume_token}/', body)

        # And the link actually works, from a brand new client.
        url = re.search(r'http://testserver(\S+)', body).group(1)
        response = self.client_class().get(url)
        self.assertRedirects(response, reverse('admissions:apply_payment'))


class ApplyResumeTests(TestCase):
    """The parent dashboard's "Continue" links — picks one of possibly
    several in-progress applications to point the session at."""

    def test_requires_login(self):
        draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche',
        )
        response = self.client.get(reverse('admissions:apply_resume', args=[draft.pk]))
        self.assertRedirects(response, f"{reverse('admissions:login')}?next={reverse('admissions:apply_resume', args=[draft.pk])}")

    def test_points_session_at_the_chosen_application(self):
        parent = _make_parent()
        draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', created_by=parent,
        )
        self.client.force_login(parent)
        response = self.client.get(reverse('admissions:apply_resume', args=[draft.pk]))
        self.assertRedirects(response, reverse('admissions:apply_payment'))
        self.assertEqual(int(self.client.session['draft_application_id']), draft.pk)

    def test_cannot_resume_someone_elses_application(self):
        owner = _make_parent(email='owner@example.com', phone='08011110000')
        other = _make_parent(email='other@example.com', phone='08022220000')
        draft = Application.objects.create(
            first_name='', last_name='', date_of_birth='2016-01-01', gender='Male',
            state_of_origin='', lga='', parent_name='', relationship='Father',
            phone='', email='', address='', applying_for='Creche', created_by=owner,
        )
        self.client.force_login(other)
        response = self.client.get(reverse('admissions:apply_resume', args=[draft.pk]))
        self.assertEqual(response.status_code, 404)


class WizardStepFormStructureTests(TestCase):
    """
    Real-browser HTML structure check, not just "does POSTing the right
    dict advance the step" — the academic step broke exactly because
    self.client.post(url, data) sends whatever dict you give it regardless
    of whether a real browser's form submission would ever have included
    those fields. A <form> that doesn't actually wrap its inputs (or
    associate them via the HTML5 form="..." attribute) silently drops them
    on submit, which client.post() can't catch since it bypasses HTML
    parsing entirely. This asserts each step's fields are genuinely inside
    a <form>...</form> block.
    """

    STEP_FIELDS = {
        'applicant': ['first_name', 'last_name', 'date_of_birth', 'gender', 'state_of_origin', 'lga'],
        'guardian': ['parent_name', 'relationship', 'phone', 'email', 'address'],
        'academic': ['applying_for', 'previous_school', 'previous_class'],
        'documents': ['passport_photo', 'birth_certificate'],
    }

    def setUp(self):
        self.client.force_login(_make_parent())
        self.client.get(reverse('admissions:apply_payment'))
        draft_id = self.client.session['draft_application_id']
        self.draft = Application.objects.get(pk=draft_id)
        ApplicationPayment.objects.create(
            invoice=self.draft.invoice, amount=self.draft.invoice.amount, status='success', gateway='manual',
        )
        self.draft.invoice.status = 'paid'
        self.draft.invoice.save(update_fields=['status'])

    def test_every_step_fields_are_inside_a_form_element(self):
        for step, field_names in self.STEP_FIELDS.items():
            with self.subTest(step=step):
                response = self.client.get(reverse(f'admissions:apply_{step}'))
                content = response.content.decode()
                forms = re.findall(r'<form\b[^>]*>(.*?)</form>', content, re.S)
                self.assertTrue(forms, f'No <form>...</form> block found on the {step} step at all.')
                for field_name in field_names:
                    in_some_form = any(f'name="{field_name}"' in form_html for form_html in forms)
                    self.assertTrue(
                        in_some_form,
                        f'Field "{field_name}" on the {step} step is not inside any <form> element — '
                        f'a real browser would silently drop it on submit.',
                    )


class NoManualBankTransferOptionTests(TestCase):
    """The Jaiz Bank self-service option is gone from every payer-facing
    payment page — ZainPay is the only way offered to pay, anywhere."""

    def test_application_payment_step_does_not_offer_bank_transfer(self):
        self.client.force_login(_make_parent())
        self.client.get(reverse('admissions:apply_payment'))
        response = self.client.get(reverse('admissions:apply_payment'))
        self.assertNotContains(response, 'Prefer bank transfer')
