from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Guardian


class ApplicantSignupTests(TestCase):
    def _post(self, **overrides):
        data = {
            'full_name': 'Ismail Bello', 'email': 'ismail@example.com', 'phone': '08012345678',
            'password1': 'a-strong-password-1', 'password2': 'a-strong-password-1',
        }
        data.update(overrides)
        return self.client.post(reverse('accounts:signup'), data)

    def test_signup_creates_user_and_guardian_and_logs_in(self):
        response = self._post()
        self.assertRedirects(response, reverse('admissions:dashboard'))

        user = User.objects.get(email='ismail@example.com')
        self.assertEqual(user.role, 'parent')
        self.assertTrue(user.check_password('a-strong-password-1'))

        guardian = Guardian.objects.get(user=user)
        self.assertEqual(guardian.name, 'Ismail Bello')
        self.assertEqual(guardian.phone, '08012345678')

        response = self.client.get(reverse('portal:home'))
        self.assertEqual(response.wsgi_request.user, user)

    def test_signup_respects_next_param(self):
        response = self.client.post(f"{reverse('accounts:signup')}", {
            'full_name': 'Ismail Bello', 'email': 'ismail@example.com', 'phone': '08012345678',
            'password1': 'a-strong-password-1', 'password2': 'a-strong-password-1',
            'next': reverse('admissions:apply_payment'),
        })
        self.assertRedirects(response, reverse('admissions:apply_payment'))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username='ismail@example.com', email='ismail@example.com', password='pw', role='parent')
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertEqual(User.objects.filter(email='ismail@example.com').count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self._post(password2='a-different-password')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='ismail@example.com').exists())

    def test_existing_userless_guardian_is_linked_not_duplicated(self):
        """An admin-managed Guardian record from an already-enrolled sibling,
        with no login yet — signup should claim it, not create a second one."""
        existing = Guardian.objects.create(name='Old Name', phone='08012345678', email='old@example.com')
        response = self._post()
        self.assertRedirects(response, reverse('admissions:dashboard'))

        existing.refresh_from_db()
        self.assertEqual(existing.name, 'Ismail Bello')
        self.assertEqual(existing.email, 'ismail@example.com')
        self.assertIsNotNone(existing.user_id)
        self.assertEqual(Guardian.objects.count(), 1)

    def test_guardian_already_linked_to_an_account_is_rejected(self):
        owner = User.objects.create_user(username='owner@example.com', email='owner@example.com', password='pw', role='parent')
        Guardian.objects.create(name='Existing Parent', phone='08012345678', email='owner@example.com', user=owner)

        response = self._post(email='different@example.com')  # same phone, different email
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertFalse(User.objects.filter(email='different@example.com').exists())
