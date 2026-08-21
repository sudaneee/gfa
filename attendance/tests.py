from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicSession, Section, SchoolClass, Term
from accounts.models import User
from attendance.models import AttendanceRecord
from staff.models import Teacher
from students.models import Student


class MarkAttendanceTests(TestCase):
    def setUp(self):
        session = AcademicSession.objects.create(name='2025/2026', is_current=True)
        self.term = Term.objects.create(session=session, name='first', is_current=True)
        school_class = SchoolClass.objects.create(name='JSS 2', level='Secondary', order=10)
        self.section = Section.objects.create(school_class=school_class, name='A')
        self.student1 = Student.objects.create(
            first_name='A', last_name='One', gender='Male', school_class=school_class, section=self.section,
        )
        self.student2 = Student.objects.create(
            first_name='B', last_name='Two', gender='Female', school_class=school_class, section=self.section,
        )
        self.teacher_user = User.objects.create_user(username='t1', password='pw', role='teacher')
        teacher = Teacher.objects.create(user=self.teacher_user, first_name='T', last_name='One', gender='Male')
        teacher.sections.set([self.section])

    def test_teacher_can_mark_and_records_persist(self):
        self.client.force_login(self.teacher_user)
        url = reverse('attendance:mark')
        response = self.client.post(url, {
            'section_id': self.section.pk, 'date': '2026-08-18',
            f'status_{self.student1.pk}': 'Present', f'status_{self.student2.pk}': 'Absent',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(AttendanceRecord.objects.get(student=self.student1).status, 'Present')
        self.assertEqual(AttendanceRecord.objects.get(student=self.student2).status, 'Absent')

    def test_resaving_the_same_date_updates_not_duplicates(self):
        self.client.force_login(self.teacher_user)
        url = reverse('attendance:mark')
        self.client.post(url, {'section_id': self.section.pk, 'date': '2026-08-18', f'status_{self.student1.pk}': 'Present'})
        self.client.post(url, {'section_id': self.section.pk, 'date': '2026-08-18', f'status_{self.student1.pk}': 'Late'})
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student1).count(), 1)
        self.assertEqual(AttendanceRecord.objects.get(student=self.student1).status, 'Late')

    def test_unauthenticated_user_is_redirected(self):
        response = self.client.get(reverse('attendance:mark'))
        self.assertEqual(response.status_code, 302)

    def test_parent_role_is_forbidden(self):
        parent_user = User.objects.create_user(username='p1', password='pw', role='parent')
        self.client.force_login(parent_user)
        response = self.client.get(reverse('attendance:mark'))
        self.assertRedirects(response, reverse('portal:home'))
