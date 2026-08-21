from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import Section, Term
from academics.utils import sections_for_user
from accounts.decorators import staff_required
from attendance.models import AttendanceRecord
from students.models import Student


@staff_required
def mark_attendance(request):
    sections = sections_for_user(request.user)
    term = Term.get_current()

    section_id = request.POST.get('section_id') or request.GET.get('section_id')
    section = sections.filter(pk=section_id).first() if section_id else sections.first()
    date_str = request.POST.get('date') or request.GET.get('date') or timezone.localdate().isoformat()

    if request.method == 'POST' and section and term:
        students = Student.objects.filter(section=section, status='Active')
        for student in students:
            status = request.POST.get(f'status_{student.pk}', 'Present')
            AttendanceRecord.objects.update_or_create(
                student=student, date=date_str,
                defaults={'section': section, 'term': term, 'status': status, 'marked_by': request.user},
            )
        messages.success(request, f'Attendance saved for {section} on {date_str}.')
        return redirect(f"{request.path}?section_id={section.pk}&date={date_str}")

    rows = []
    if section:
        existing = {
            r.student_id: r.status
            for r in AttendanceRecord.objects.filter(section=section, date=date_str)
        }
        for student in Student.objects.filter(section=section, status='Active'):
            rows.append({'student': student, 'status': existing.get(student.id, 'Present')})

    return render(request, 'attendance/mark.html', {
        'sections': sections, 'section': section, 'date': date_str, 'rows': rows,
        'no_current_term': term is None,
    })


@staff_required
def attendance_records(request):
    sections = sections_for_user(request.user)
    section_id = request.GET.get('section_id')
    date_str = request.GET.get('date', '')

    records = AttendanceRecord.objects.filter(section__in=sections).select_related('student', 'section')
    if section_id:
        records = records.filter(section_id=section_id)
    if date_str:
        records = records.filter(date=date_str)
    records = records.order_by('-date', 'student__last_name')[:200]

    return render(request, 'attendance/records.html', {
        'sections': sections, 'records': records, 'section_id': section_id, 'date': date_str,
    })
