from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Student
from website.models import SchoolSettings


class ReportsAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='a1', password='pw', role='admin')
        self.teacher = User.objects.create_user(username='t1', password='pw', role='teacher')
        self.parent = User.objects.create_user(username='p1', password='pw', role='parent')

    def test_admin_can_view_reports(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('portal:reports'))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_roles_are_redirected(self):
        for user in (self.teacher, self.parent):
            self.client.force_login(user)
            response = self.client.get(reverse('portal:reports'))
            self.assertRedirects(response, reverse('portal:home'))

    def test_settings_and_reset_are_admin_only(self):
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get(reverse('portal:settings')), reverse('portal:home'))
        self.assertRedirects(self.client.post(reverse('portal:reset_demo_data')), reverse('portal:home'))


class ResetDemoDataTests(TestCase):
    """The reset command must never touch user accounts or school configuration."""

    def test_reset_preserves_users_and_school_settings(self):
        call_command('seed_demo_users')
        school = SchoolSettings.get_solo()
        school.name = 'Custom Renamed Academy'  # simulate an admin customization
        school.save()

        user_count_before = User.objects.count()
        call_command('reset_demo_data')

        self.assertEqual(User.objects.count(), user_count_before)
        self.assertTrue(User.objects.filter(email='admin@gfa.edu.ng').exists())
        school.refresh_from_db()
        self.assertEqual(school.name, 'Custom Renamed Academy')

    def test_reset_produces_a_non_empty_dataset(self):
        call_command('seed_demo_users')
        call_command('reset_demo_data')
        self.assertGreater(Student.objects.count(), 0)

    def test_reset_is_safe_to_run_twice_in_a_row(self):
        call_command('seed_demo_users')
        call_command('reset_demo_data')
        first_count = Student.objects.count()
        call_command('reset_demo_data')
        self.assertEqual(Student.objects.count(), first_count)
