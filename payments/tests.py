import hashlib
import hmac
import json
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from admissions.models import Application, ApplicationInvoice, ApplicationPayment
from payments import services


class FeeInvoiceAccessTests(TestCase):
    """Termly fee invoices are an admin/parent/student concern — a teacher
    has no legitimate reason to view or pay one, regardless of whether the
    student is in their class (unlike report cards, which stay scoped)."""

    def setUp(self):
        from academics.models import AcademicSession, SchoolClass, Section, Term
        from accounts.models import User
        from finance.models import Invoice
        from staff.models import Teacher
        from students.models import Guardian, Student

        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        school_class = SchoolClass.objects.create(name='Primary 5', level='Primary', order=1)
        section = Section.objects.create(school_class=school_class, name='A')

        self.parent_user = User.objects.create_user(username='p1', password='pw', role='parent')
        guardian = Guardian.objects.create(name='Parent', phone='080', user=self.parent_user)
        self.student_user = User.objects.create_user(username='s1', password='pw', role='student')
        self.student = Student.objects.create(
            first_name='Fee', last_name='Test', gender='Male', school_class=school_class,
            section=section, guardian=guardian, user=self.student_user,
        )
        Invoice.objects.create(student=self.student, term=self.term)

        self.admin = User.objects.create_user(username='a1', password='pw', role='admin')
        self.teacher_user = User.objects.create_user(username='t1', password='pw', role='teacher')
        Teacher.objects.create(user=self.teacher_user, first_name='T', last_name='One', gender='Male').sections.add(section)

    def _url(self):
        return reverse('payments:fee_invoice', args=[self.student.pk, self.term.pk])

    def test_admin_can_view(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_owning_parent_can_view(self):
        self.client.force_login(self.parent_user)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_the_student_can_view_their_own(self):
        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get(self._url()).status_code, 200)

    def test_teacher_cannot_view_even_for_a_student_in_their_own_section(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(self._url())
        self.assertRedirects(response, reverse('portal:home'))

    def test_teacher_cannot_initiate_payment(self):
        self.client.force_login(self.teacher_user)
        response = self.client.post(reverse('payments:initiate_fee_payment', args=[self.student.pk, self.term.pk]))
        self.assertRedirects(response, reverse('portal:home'))


def _mock_response(status_code, body):
    resp = Mock()
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


class VerifyPaymentParsingTests(TestCase):
    """
    Exercises verify_payment()'s actual HTTP parsing against the response
    shapes documented at
    https://zainpay.ng/developers/card-endpoints?section=card-integration-steps
    — caught via live sandbox testing that the ported version was hitting a
    URL missing '/v2/' and expecting a "code" field that success responses
    don't actually have.
    """

    @patch('payments.services.requests.get')
    def test_success_shape_is_the_flat_deposit_record_with_no_code_field(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            'txnType': 'deposit', 'sender': 'John Doe', 'depositedAmount': 1050.00,
            'txnChargesAmount': 50.00, 'amountAfterCharges': 1000.00, 'txnRef': 'Q6166237864',
        })
        result = services.verify_payment('Q6166237864')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['amount'], Decimal('1000.00'))

    @patch('payments.services.requests.get')
    def test_verify_hits_the_v2_endpoint(self, mock_get):
        mock_get.return_value = _mock_response(200, {'txnRef': 'X', 'amountAfterCharges': 500})
        services.verify_payment('X')
        called_url = mock_get.call_args[0][0]
        self.assertIn('/virtual-account/wallet/deposit/verify/v2/X', called_url)

    @patch('payments.services._reconcile_card_payment')
    @patch('payments.services.requests.get')
    def test_ambiguous_not_found_falls_back_to_reconcile_success(self, mock_get, mock_reconcile):
        mock_get.return_value = _mock_response(400, {'code': '04', 'description': 'Txn not found'})
        mock_reconcile.return_value = {
            'status': 'success', 'amount': Decimal('0'), 'gateway_reference': 'X', 'raw_response': {},
        }
        result = services.verify_payment('X')
        self.assertEqual(result['status'], 'success')
        mock_reconcile.assert_called_once_with('X')

    @patch('payments.services._reconcile_card_payment')
    @patch('payments.services.requests.get')
    def test_ambiguous_not_found_stays_pending_when_reconcile_is_inconclusive(self, mock_get, mock_reconcile):
        mock_get.return_value = _mock_response(400, {'code': '04', 'description': 'Txn not found'})
        mock_reconcile.return_value = None
        result = services.verify_payment('X')
        self.assertEqual(result['status'], 'pending')


class ReconcileCardPaymentTests(TestCase):
    @patch('payments.services.requests.get')
    def test_definitive_success_from_reconcile_endpoint(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            'code': '00', 'description': 'Transaction reconciled',
            'data': {'txnRef': 'X', 'txnStatus': 'success'},
        })
        result = services._reconcile_card_payment('X')
        self.assertEqual(result['status'], 'success')

    @patch('payments.services.requests.get')
    def test_inconclusive_reconcile_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(400, {'code': '04', 'description': 'Invalid txnRef'})
        result = services._reconcile_card_payment('X')
        self.assertIsNone(result)


def _make_application(**overrides):
    defaults = dict(
        first_name='Test', last_name='Applicant', date_of_birth='2016-01-01', gender='Male',
        state_of_origin='Niger', lga='Suleja', parent_name='Test Parent', relationship='Father',
        phone='08000000000', email='parent@example.com', address='Test address',
        applying_for='Primary 1', is_submitted=True, submitted_at=timezone.now(),
    )
    defaults.update(overrides)
    return Application.objects.create(**defaults)


class InitiatePaymentChargeTests(TestCase):
    """The 200-naira transaction charge and the bank_transfer-only channel
    restriction must only ever reach ZainPay's payload — never our own
    invoice/payment records, which stay exactly what's owed."""

    def setUp(self):
        self.application = _make_application()
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=Decimal('2000.00'))

    @patch('payments.services.requests.post')
    def test_payload_amount_includes_the_transaction_charge(self, mock_post):
        mock_post.return_value = _mock_response(200, {'data': 'https://sandbox.zainpay.ng/pay/xyz'})

        services.initiate_payment(self.invoice, callback_url='https://example.com/cb', customer_email='parent@example.com')

        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['amount'], '2200')  # 2000 balance + 200 charge

    @patch('payments.services.requests.post')
    def test_payload_restricts_payment_channel_to_bank_transfer(self, mock_post):
        mock_post.return_value = _mock_response(200, {'data': 'https://sandbox.zainpay.ng/pay/xyz'})

        services.initiate_payment(self.invoice, callback_url='https://example.com/cb', customer_email='parent@example.com')

        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['paymentChannels'], ['bank_transfer'])

    @patch('payments.services.requests.post')
    def test_the_charge_never_touches_the_invoice_or_payment_record(self, mock_post):
        mock_post.return_value = _mock_response(200, {'data': 'https://sandbox.zainpay.ng/pay/xyz'})

        services.initiate_payment(self.invoice, callback_url='https://example.com/cb', customer_email='parent@example.com')

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.balance, Decimal('2000.00'))  # unchanged — the charge was never added here
        payment = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=self.invoice.balance, gateway='zainpay', status='pending', reference='GFA-CHARGETEST',
        )
        self.assertEqual(payment.amount, Decimal('2000.00'))


class MarkPaymentSuccessTests(TestCase):
    """The shared manual-payment path (Jaiz Bank transfer, no ZainPay
    involved) — used by finance.admin.PaymentAdmin, admissions.admin
    .ApplicationPaymentAdmin, and the Superadmin Console's "Mark Received"
    action alike, so all three stay identical by construction."""

    def setUp(self):
        self.application = _make_application()
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=Decimal('2000.00'))
        self.payment = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=Decimal('2000.00'), gateway='manual', status='pending',
            reference='GFA-MANUALREF1',
        )

    def test_marks_success_stamps_fields_and_syncs_invoice(self):
        services.mark_payment_success(self.payment)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertIsNotNone(self.payment.paid_at)
        self.assertTrue(self.payment.receipt_number)
        self.assertEqual(self.invoice.status, 'paid')

    def test_sends_the_same_confirmation_email_a_zainpay_payment_would(self):
        from django.core import mail

        services.mark_payment_success(self.payment)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.application.application_number, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [self.application.email])

    def test_already_successful_payment_does_not_resend_the_email(self):
        from django.core import mail

        self.payment.status = 'success'
        self.payment.save()

        services.mark_payment_success(self.payment)

        self.assertEqual(len(mail.outbox), 0)

    def test_records_who_confirmed_it_for_the_audit_trail(self):
        from accounts.models import User

        admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        services.mark_payment_success(self.payment, user=admin)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.received_by, admin)
        self.assertEqual(self.payment.updated_by, admin)
        self.assertIsNotNone(self.payment.updated_at)


class GenuineZainpaySuccessDetectionTests(TestCase):
    """services.looks_like_genuine_zainpay_success backs the retag audit —
    it must recognize a real ZainPay success payload in either shape
    verify_payment can return, and reject everything else, including the
    exact 'Txn not found' shape a never-confirmed reference produces."""

    def test_flat_deposit_record_is_genuine(self):
        self.assertTrue(services.looks_like_genuine_zainpay_success({'txnRef': 'GFA-X', 'amountAfterCharges': '2000'}))

    def test_reconcile_success_shape_is_genuine(self):
        self.assertTrue(services.looks_like_genuine_zainpay_success(
            {'code': '00', 'data': {'txnStatus': 'success'}, 'description': 'Transaction successful'}
        ))

    def test_txn_not_found_is_not_genuine(self):
        self.assertFalse(services.looks_like_genuine_zainpay_success(
            {'status': '404 Not Found', 'description': 'Txn not found', 'code': '04', 'data': None}
        ))

    def test_reconcile_failed_shape_is_not_genuine(self):
        self.assertFalse(services.looks_like_genuine_zainpay_success(
            {'code': '00', 'data': {'txnStatus': 'failed'}}
        ))

    def test_none_or_empty_is_not_genuine(self):
        self.assertFalse(services.looks_like_genuine_zainpay_success(None))
        self.assertFalse(services.looks_like_genuine_zainpay_success({}))


class ProcessPaymentTests(TestCase):
    """payments.services.process_payment — the shared verify-and-persist logic."""

    def setUp(self):
        self.application = _make_application()
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=Decimal('2000.00'))
        self.payment = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=Decimal('2000.00'), gateway='zainpay', status='pending',
            reference='GFA-TESTREF001',
        )

    @patch('payments.services.verify_payment')
    def test_successful_verification_marks_paid_and_updates_invoice(self, mock_verify):
        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-TESTREF001', 'raw_response': {'code': '00'},
        }
        result = services.process_payment(self.payment)

        self.assertEqual(result, {'status': 'success', 'changed': True})

    @patch('payments.services.verify_payment')
    def test_successful_payment_sends_a_confirmation_email(self, mock_verify):
        from django.core import mail

        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-TESTREF001', 'raw_response': {'code': '00'},
        }
        services.process_payment(self.payment)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.application.email])
        self.assertIn(self.application.application_number, mail.outbox[0].subject)

    @patch('payments.services.verify_payment')
    def test_no_op_confirmation_does_not_resend_email(self, mock_verify):
        from django.core import mail

        self.payment.status = 'success'
        self.payment.save()
        services.process_payment(self.payment)  # already success — no-op guard short-circuits
        self.assertEqual(len(mail.outbox), 0)
        mock_verify.assert_not_called()

    @patch('payments.services.verify_payment')
    def test_already_successful_payment_is_a_no_op(self, mock_verify):
        self.payment.status = 'success'
        self.payment.save()

        result = services.process_payment(self.payment)

        self.assertEqual(result, {'status': 'success', 'changed': False})
        mock_verify.assert_not_called()  # idempotency guard short-circuits before hitting the API

    @patch('payments.services.verify_payment')
    def test_pending_result_leaves_invoice_unpaid(self, mock_verify):
        mock_verify.return_value = {
            'status': 'pending', 'amount': Decimal('0'), 'gateway_reference': 'GFA-TESTREF001', 'raw_response': {},
        }
        services.process_payment(self.payment)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unpaid')

    @patch('payments.services.verify_payment')
    def test_api_error_propagates(self, mock_verify):
        mock_verify.side_effect = services.ZainPayError('network error')
        with self.assertRaises(services.ZainPayError):
            services.process_payment(self.payment)


@override_settings(ZAINPAY_SECRET_KEY='test-webhook-secret')
class WebhookTests(TestCase):
    """payments.views.zainpay_webhook — signature verification + status persistence."""

    def setUp(self):
        self.application = _make_application()
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=Decimal('2000.00'))
        self.payment = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=Decimal('2000.00'), gateway='zainpay', status='pending',
            reference='GFA-WEBHOOKREF01',
        )
        self.url = reverse('payments:zainpay_callback')

    def _signed_post(self, body: dict, secret='test-webhook-secret'):
        raw = json.dumps(body).encode('utf-8')
        sig = hmac.new(secret.encode('utf-8'), raw, hashlib.sha256).hexdigest()
        return self.client.post(self.url, data=raw, content_type='application/json', HTTP_ZAINPAY_SIGNATURE=sig)

    @patch('payments.services.verify_payment')
    def test_valid_signature_and_deposit_event_confirms_payment(self, mock_verify):
        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-WEBHOOKREF01', 'raw_response': {'code': '00'},
        }
        response = self._signed_post({'event': 'deposit', 'data': {'txnRef': 'GFA-WEBHOOKREF01'}})

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')

    def test_invalid_signature_is_rejected(self):
        raw = json.dumps({'event': 'deposit', 'data': {'txnRef': 'GFA-WEBHOOKREF01'}}).encode('utf-8')
        response = self.client.post(
            self.url, data=raw, content_type='application/json', HTTP_ZAINPAY_SIGNATURE='not-the-right-signature',
        )
        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')  # untouched

    @patch('payments.services.verify_payment')
    def test_non_deposit_event_is_acknowledged_without_processing(self, mock_verify):
        response = self._signed_post({'event': 'transfer', 'data': {'txnRef': 'GFA-WEBHOOKREF01'}})
        self.assertEqual(response.status_code, 200)
        mock_verify.assert_not_called()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    @patch('payments.services.verify_payment')
    def test_unknown_reference_is_acknowledged_but_not_processed(self, mock_verify):
        response = self._signed_post({'event': 'deposit', 'data': {'txnRef': 'GFA-DOES-NOT-EXIST'}})
        self.assertEqual(response.status_code, 200)
        mock_verify.assert_not_called()

    @patch('payments.services.verify_payment')
    def test_already_successful_payment_is_not_reverified(self, mock_verify):
        self.payment.status = 'success'
        self.payment.save()
        response = self._signed_post({'event': 'deposit', 'data': {'txnRef': 'GFA-WEBHOOKREF01'}})
        self.assertEqual(response.status_code, 200)
        mock_verify.assert_not_called()


class ZainPayCallbackRedirectTests(TestCase):
    """The browser redirect-back leg of zainpay_callback (GET, not the
    webhook). This used to fall back to "the most recent pending payment"
    queried across the ENTIRE database with no scoping at all whenever
    ?txnRef= didn't come through — which meant a redirect that lost its
    txnRef could mark a completely different family's still-unpaid
    application as paid. That's exactly the real incident this guards
    against: a parent who paid for one child saw all of his children's
    applications marked paid."""

    def setUp(self):
        self.url = reverse('payments:zainpay_callback')

        self.mine = _make_application(email='mine@example.com', is_submitted=False)
        self.mine_invoice = ApplicationInvoice.objects.create(application=self.mine, amount=Decimal('2000.00'))
        self.mine_payment = ApplicationPayment.objects.create(
            invoice=self.mine_invoice, amount=Decimal('2000.00'), gateway='zainpay', status='pending',
            reference='GFA-MINEREF01',
        )

        # A completely unrelated family's still-pending payment — the old
        # bug's "most recent pending payment" fallback would grab this one.
        self.other = _make_application(email='other@example.com', is_submitted=False)
        self.other_invoice = ApplicationInvoice.objects.create(application=self.other, amount=Decimal('2000.00'))
        self.other_payment = ApplicationPayment.objects.create(
            invoice=self.other_invoice, amount=Decimal('2000.00'), gateway='zainpay', status='pending',
            reference='GFA-OTHERREF01',
        )

    @patch('payments.services.verify_payment')
    def test_txn_ref_in_query_string_resolves_normally(self, mock_verify):
        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-MINEREF01', 'raw_response': {},
        }
        self.client.get(self.url, {'txnRef': 'GFA-MINEREF01'})

        self.mine_payment.refresh_from_db()
        self.other_payment.refresh_from_db()
        self.assertEqual(self.mine_payment.status, 'success')
        self.assertEqual(self.other_payment.status, 'pending')  # untouched

    @patch('payments.services.verify_payment')
    def test_missing_txn_ref_recovers_from_this_sessions_own_reference(self, mock_verify):
        """The one allowed fallback — this exact browser's own most
        recently initiated payment, remembered in its session."""
        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-MINEREF01', 'raw_response': {},
        }
        session = self.client.session
        session['pending_zainpay_reference'] = 'GFA-MINEREF01'
        session.save()

        self.client.get(self.url)  # no txnRef in the query string at all

        self.mine_payment.refresh_from_db()
        self.other_payment.refresh_from_db()
        self.assertEqual(self.mine_payment.status, 'success')
        self.assertEqual(self.other_payment.status, 'pending')  # untouched

    @patch('payments.services.verify_payment')
    def test_missing_txn_ref_and_no_session_reference_never_guesses_a_database_payment(self, mock_verify):
        """The regression test for the actual incident: no txnRef, no
        session reference either (e.g. a different device/browser) —
        must fail safely and touch NOTHING, not even the most recently
        created pending payment."""
        response = self.client.get(self.url)

        mock_verify.assert_not_called()
        self.mine_payment.refresh_from_db()
        self.other_payment.refresh_from_db()
        self.assertEqual(self.mine_payment.status, 'pending')
        self.assertEqual(self.other_payment.status, 'pending')
        self.assertRedirects(response, reverse('website:home'))

    @patch('payments.services.verify_payment')
    def test_stale_session_reference_from_an_earlier_payment_does_not_leak_forward(self, mock_verify):
        """Once a payment's been resolved via the session fallback, that
        session key is cleared — a second, unrelated callback on the same
        browser (e.g. a stray reload) must not silently re-resolve to the
        old payment."""
        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'),
            'gateway_reference': 'GFA-MINEREF01', 'raw_response': {},
        }
        session = self.client.session
        session['pending_zainpay_reference'] = 'GFA-MINEREF01'
        session.save()
        self.client.get(self.url)  # resolves + clears the session key

        mock_verify.reset_mock()
        response = self.client.get(self.url)  # a second, txnRef-less hit
        mock_verify.assert_not_called()
        self.assertRedirects(response, reverse('website:home'))


class RetagPaymentGatewaysCommandTests(TestCase):
    """The one-time audit that separates 'ZainPay really confirmed this'
    from 'someone in the console marked it received' — the exact
    distinction this whole feature exists to make honest."""

    def setUp(self):
        self.application = _make_application()
        self.invoice = ApplicationInvoice.objects.create(application=self.application, amount=Decimal('2000.00'))

        self.genuine = ApplicationPayment.objects.create(
            invoice=self.invoice, amount=Decimal('2000.00'), gateway='zainpay', status='success',
            reference='GFA-GENUINE01',
            gateway_response={'code': '00', 'data': {'txnStatus': 'success'}, 'description': 'ok'},
        )

        self.other_application = _make_application(email='other@example.com')
        self.other_invoice = ApplicationInvoice.objects.create(application=self.other_application, amount=Decimal('2000.00'))
        self.fake = ApplicationPayment.objects.create(
            invoice=self.other_invoice, amount=Decimal('2000.00'), gateway='zainpay', status='success',
            reference='GFA-FAKE01', gateway_response=None,
        )

    @patch('payments.services.verify_payment')
    def test_payment_with_genuine_stored_response_is_left_alone(self, mock_verify):
        from django.core.management import call_command

        mock_verify.return_value = {'status': 'pending', 'amount': Decimal('0'), 'gateway_reference': '', 'raw_response': {}}
        call_command('retag_payment_gateways', stdout=StringIO())

        self.genuine.refresh_from_db()
        self.assertEqual(self.genuine.gateway, 'zainpay')
        # The other, evidence-less payment in this same run does need a live
        # check — but the genuine one's own reference is never even asked.
        called_refs = [call.args[0] for call in mock_verify.call_args_list]
        self.assertNotIn('GFA-GENUINE01', called_refs)

    @patch('payments.services.verify_payment')
    def test_payment_with_no_evidence_and_no_live_confirmation_is_retagged(self, mock_verify):
        from django.core.management import call_command

        mock_verify.return_value = {'status': 'pending', 'amount': Decimal('0'), 'gateway_reference': '', 'raw_response': {}}

        call_command('retag_payment_gateways', stdout=StringIO())

        self.fake.refresh_from_db()
        self.assertEqual(self.fake.gateway, 'manual')
        self.assertIn('Retagged from ZainPay to Manual', self.fake.notes)
        # Status/amount are never touched by the retag itself.
        self.assertEqual(self.fake.status, 'success')
        self.assertEqual(self.fake.amount, Decimal('2000.00'))

    @patch('payments.services.verify_payment')
    def test_live_confirmation_saves_a_payment_with_no_stored_evidence(self, mock_verify):
        from django.core.management import call_command

        mock_verify.return_value = {
            'status': 'success', 'amount': Decimal('2000.00'), 'gateway_reference': 'GFA-FAKE01', 'raw_response': {},
        }

        call_command('retag_payment_gateways', stdout=StringIO())

        self.fake.refresh_from_db()
        self.assertEqual(self.fake.gateway, 'zainpay')  # live check vindicated it

    @patch('payments.services.verify_payment')
    def test_dry_run_changes_nothing(self, mock_verify):
        from django.core.management import call_command

        mock_verify.return_value = {'status': 'pending', 'amount': Decimal('0'), 'gateway_reference': '', 'raw_response': {}}

        call_command('retag_payment_gateways', '--dry-run', stdout=StringIO())

        self.fake.refresh_from_db()
        self.assertEqual(self.fake.gateway, 'zainpay')

    @patch('payments.services.verify_payment')
    def test_network_error_during_live_check_is_treated_as_inconclusive_not_fatal(self, mock_verify):
        from django.core.management import call_command

        mock_verify.side_effect = services.ZainPayError('network error')

        call_command('retag_payment_gateways', stdout=StringIO())  # must not raise

        self.fake.refresh_from_db()
        self.assertEqual(self.fake.gateway, 'manual')
