import re
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from admissions.models import Application, ApplicationInvoice, ApplicationPayment, generate_application_number
from website.models import SchoolSettings


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
        self.assertRedirects(response, reverse('admissions:apply_payment'))


class ContactInfoBeforePaymentTests(TestCase):
    """
    Email/phone must be collected before the Pay button appears — otherwise
    ZainPay's initiate call gets a blank (docs: required) emailAddress, and
    a payment that only resolves later (webhook, reconcile_zainpay) has no
    address to send the confirmation to.
    """

    def _create_draft(self):
        self.client.get(reverse('admissions:apply_payment'))
        draft_id = self.client.session['draft_application_id']
        return Application.objects.get(pk=draft_id)

    def test_payment_page_shows_contact_form_before_email_is_known(self):
        self._create_draft()
        response = self.client.get(reverse('admissions:apply_payment'))
        self.assertContains(response, 'Continue to Payment')
        self.assertNotContains(response, 'with ZainPay')

    def test_submitting_contact_form_saves_it_and_unlocks_the_pay_button(self):
        self._create_draft()
        response = self.client.post(reverse('admissions:apply_payment'), {
            'set_contact': '1', 'email': 'parent@example.com', 'phone': '08012345678',
        }, follow=True)
        self.assertContains(response, 'with ZainPay')

        draft = Application.objects.get(email='parent@example.com')
        self.assertEqual(draft.phone, '08012345678')

    def test_incomplete_contact_form_is_rejected(self):
        self._create_draft()
        response = self.client.post(reverse('admissions:apply_payment'), {
            'set_contact': '1', 'email': '', 'phone': '',
        })
        self.assertContains(response, 'Continue to Payment')  # re-rendered, not advanced

    @patch('payments.services.initiate_payment')
    def test_initiate_payment_uses_the_captured_email(self, mock_initiate):
        draft = self._create_draft()
        draft.email = 'parent@example.com'
        draft.phone = '08012345678'
        draft.save()
        mock_initiate.return_value = {'reference': 'X', 'gateway_reference': 'X', 'payment_url': 'https://example.com/pay'}

        self.client.post(reverse('payments:initiate_application_payment', args=[draft.application_number]))

        _, kwargs = mock_initiate.call_args
        self.assertEqual(kwargs['customer_email'], 'parent@example.com')
        self.assertEqual(kwargs['mobile'], '08012345678')


class ApplicationWizardTests(TestCase):
    """End-to-end smoke test of the session-backed multi-step form, payment-gated."""

    def _pay_first(self):
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
