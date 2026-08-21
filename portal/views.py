from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from academics.models import Term
from accounts.decorators import admin_required


def _admin_dashboard_context():
    """Everything the Superadmin control-center home page needs — stat
    cards, charts, and recent activity, all built from the models that
    already exist rather than anything new. Reuses the same query shapes
    as portal.reports so the two views can never quietly disagree."""
    from accounts.models import User
    from admissions.models import Application
    from communication.models import Announcement
    from finance.models import Invoice, Payment
    from staff.models import Teacher
    from students.models import Guardian, Student

    term = Term.get_current()
    today = timezone.localdate()

    active_students = Student.objects.filter(status='Active')
    active_teachers = Teacher.objects.filter(status='Active')
    open_applications = Application.objects.filter(is_submitted=True) \
        .exclude(status__in=['approved', 'rejected', 'admitted'])

    invoices = Invoice.objects.filter(term=term) if term else Invoice.objects.none()
    total_billed = sum((inv.total for inv in invoices), start=0)
    total_collected = sum((inv.amount_paid for inv in invoices), start=0)
    total_outstanding = total_billed - total_collected

    todays_attendance = None
    if term:
        from attendance.models import AttendanceRecord
        att_qs = AttendanceRecord.objects.filter(term=term, date=today)
        att_total = att_qs.count()
        todays_attendance = round(att_qs.filter(status='Present').count() / att_total * 100) if att_total else None

    enrollment_by_level = list(
        active_students.values('school_class__level').annotate(count=Count('id')).order_by('school_class__level')
    )

    six_months_ago = today.replace(day=1) - timezone.timedelta(days=180)
    revenue_by_month = list(
        Payment.objects.filter(status='success', created_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at')).values('month')
        .annotate(total=Sum('amount')).order_by('month')
    )

    status_labels = dict(Application.STATUS_CHOICES)
    application_pipeline = [
        {**row, 'label': status_labels.get(row['status'], row['status'])}
        for row in Application.objects.filter(is_submitted=True).values('status').annotate(count=Count('id')).order_by('status')
    ]

    return {
        'total_students': active_students.count(),
        'total_teachers': active_teachers.count(),
        'total_parents': Guardian.objects.count(),
        'total_users': User.objects.count(),
        'open_applications': open_applications.count(),
        'fees_collected_term': total_collected,
        'fees_outstanding_term': total_outstanding,
        'todays_attendance_rate': todays_attendance,
        'enrollment_by_level': enrollment_by_level,
        'max_enrollment_level': max((r['count'] for r in enrollment_by_level), default=0),
        'revenue_by_month': revenue_by_month,
        'max_month_revenue': max((r['total'] for r in revenue_by_month), default=0),
        'application_pipeline': application_pipeline,
        'recent_applications': Application.objects.filter(is_submitted=True).order_by('-submitted_at')[:5],
        'recent_payments': Payment.objects.filter(status='success').select_related('invoice__student').order_by('-created_at')[:5],
        'recent_announcements': Announcement.objects.filter(is_published=True).order_by('-created_at')[:3],
    }


@login_required
def home(request):
    """
    Role-based landing page. Admins get a full control-center dashboard
    (stat cards, charts, recent activity, quick links across every module);
    the other three roles keep their existing focused quick-link views.
    """
    context = {'role': request.user.role, 'current_term': Term.get_current(), 'active_nav': 'home'}
    if request.user.role == 'admin':
        context.update(_admin_dashboard_context())
    elif request.user.role == 'teacher':
        context['teacher'] = getattr(request.user, 'teacher_profile', None)
    elif request.user.role == 'parent':
        context['guardian'] = getattr(request.user, 'guardian_profile', None)
    elif request.user.role == 'student':
        context['student'] = getattr(request.user, 'student_profile', None)
    return render(request, 'portal/home.html', context)


@admin_required
def reports(request):
    from academics.models import Subject
    from attendance.models import AttendanceRecord
    from finance.models import Invoice
    from results.models import GradeBoundary, Result
    from students.models import Student

    term = Term.get_current()
    active_students = Student.objects.filter(status='Active')

    # ── Student reports ──────────────────────────────────────────────────
    by_level = list(
        active_students.values('school_class__level').annotate(count=Count('id')).order_by('school_class__level')
    )
    by_gender = list(active_students.values('gender').annotate(count=Count('id')))
    by_class = list(
        active_students.values('school_class__name').annotate(count=Count('id')).order_by('school_class__order')
    )
    new_admissions = active_students.filter(admission_date__year=timezone.localdate().year).count()

    # ── Academic reports ─────────────────────────────────────────────────
    class_performance = []
    grade_distribution = []
    if term:
        class_performance = list(
            Result.objects.filter(term=term, student__status='Active')
            .values('student__school_class__name')
            .annotate(avg_total=Avg('total'))
            .order_by('student__school_class__order')
        )
        grade_distribution = list(
            Result.objects.filter(term=term).values('grade').annotate(count=Count('id')).order_by('-grade')
        )

    # ── Financial reports ────────────────────────────────────────────────
    invoices = Invoice.objects.filter(term=term) if term else Invoice.objects.none()
    total_billed = sum((inv.total for inv in invoices), start=0)
    total_collected = sum((inv.amount_paid for inv in invoices), start=0)
    total_outstanding = total_billed - total_collected
    fees_by_band = []
    if term:
        for band_name in ['Nursery', 'Primary', 'Junior Secondary', 'Senior Secondary']:
            band_invoices = [inv for inv in invoices if inv.student.school_class.fee_band and inv.student.school_class.fee_band.name == band_name]
            fees_by_band.append({
                'band': band_name,
                'collected': sum((inv.amount_paid for inv in band_invoices), start=0),
            })

    # ── Attendance reports ───────────────────────────────────────────────
    attendance_qs = AttendanceRecord.objects.filter(term=term) if term else AttendanceRecord.objects.none()
    total_att = attendance_qs.count()
    present_att = attendance_qs.filter(status='Present').count()
    absent_att = attendance_qs.filter(status='Absent').count()
    daily_trend = list(
        attendance_qs.values('date')
        .annotate(total=Count('id'), present=Count('id', filter=Q(status='Present')))
        .order_by('date')
    )

    return render(request, 'portal/reports.html', {
        'term': term,
        'total_students': active_students.count(), 'by_level': by_level, 'by_gender': by_gender,
        'by_class': by_class, 'new_admissions': new_admissions,
        'class_performance': class_performance, 'grade_distribution': grade_distribution,
        'total_billed': total_billed, 'total_collected': total_collected,
        'total_outstanding': total_outstanding, 'fees_by_band': fees_by_band,
        'total_attendance': total_att, 'present_rate': round(present_att / total_att * 100) if total_att else 0,
        'absent_rate': round(absent_att / total_att * 100) if total_att else 0, 'daily_trend': daily_trend,
    })


@admin_required
def settings_view(request):
    from results.models import GradeBoundary
    from website.models import SchoolSettings

    return render(request, 'portal/settings.html', {
        'school': SchoolSettings.get_solo(), 'grade_boundaries': GradeBoundary.objects.all(),
        'active_nav': 'settings',
    })


@admin_required
def settings_edit(request):
    from django.forms import modelform_factory

    from website.models import SchoolSettings

    school = SchoolSettings.get_solo()
    Form = modelform_factory(SchoolSettings, fields=[
        'name', 'tagline', 'slogan', 'address', 'email', 'phone_numbers', 'approvals', 'logo',
        'bank_name', 'bank_account_number', 'bank_account_name', 'current_session', 'application_fee',
    ])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'School information updated.')
            return redirect('portal:settings')
    else:
        form = Form(instance=school)
    return render(request, 'portal/settings_edit.html', {'form': form, 'active_nav': 'settings'})


@admin_required
@require_POST
def reset_demo_data_view(request):
    call_command('reset_demo_data')
    messages.success(request, 'Demo data has been reset successfully.')
    return redirect('portal:settings')
