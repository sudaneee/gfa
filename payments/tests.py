import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from admissions.models import Application, ApplicationInvoice, ApplicationPayment
from payments import services


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
