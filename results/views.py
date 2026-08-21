from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from academics.models import AcademicSession, Subject, Term
from academics.utils import sections_for_user
from accounts.decorators import staff_required, role_required
from results.models import GradeBoundary, Result, ScoreComponent
from results.services import class_broadsheet, save_result_scores, student_position
from students.models import Student


def _get_by_pk(queryset, pk):
    """queryset.filter(pk=pk).first(), but tolerant of a missing/blank/
    malformed pk from a query string instead of raising ValueError."""
    if not pk:
        return None
    try:
        return queryset.filter(pk=pk).first()
    except (ValueError, TypeError):
        return None


def _resolve_selectors(request, sections, default_section=True):
    """Cascading Session -> Term -> Class -> Subject, all overridable via
    GET/POST so historical results stay reachable (not just "current
    term"). Session/Term default to the current one when nothing was
    explicitly chosen — that's just a convenient pre-fill, not "results".
    Class/Subject only default to the first option when `default_section`
    is True (the summary pages); the entry/update grids pass False so
    nothing loads until the teacher explicitly picks a class+subject and
    clicks Load — see _results_grid. An explicit but invalid/blank id
    always resolves to None rather than silently substituting a default,
    so a stale selection doesn't quietly point somewhere else."""
    sessions = AcademicSession.objects.all()
    current_term = Term.get_current()

    session_id = request.POST.get('session_id') or request.GET.get('session_id')
    session = _get_by_pk(sessions, session_id) or (
        (current_term.session if current_term else sessions.first()) if not session_id else None
    )

    terms = Term.objects.filter(session=session).select_related('session') if session else Term.objects.none()
    term_id = request.POST.get('term_id') or request.GET.get('term_id')
    if term_id:
        term = _get_by_pk(terms, term_id)
    else:
        term = current_term if (current_term and session and current_term.session_id == session.id) else terms.first()

    section_id = request.POST.get('section_id') or request.GET.get('section_id')
    if section_id:
        section = _get_by_pk(sections, section_id)
    else:
        section = sections.first() if default_section else None

    subjects = Subject.objects.filter(level=section.school_class.level) if section else Subject.objects.none()
    subject_id = request.POST.get('subject_id') or request.GET.get('subject_id')
    if subject_id:
        subject = _get_by_pk(subjects, subject_id)
    else:
        subject = subjects.first() if (default_section and section) else None

    return {
        'sessions': sessions, 'session': session, 'terms': terms, 'term': term,
        'sections': sections, 'section': section, 'subjects': subjects, 'subject': subject,
    }


def _results_grid(request, *, existing_only, template_name, active_nav):
    sections = sections_for_user(request.user)
    sel = _resolve_selectors(request, sections, default_section=False)
    session, term, section, subject = sel['session'], sel['term'], sel['section'], sel['subject']
    components = list(ScoreComponent.objects.order_by('order'))

    if request.method == 'POST' and section and subject and term:
        targets = Student.objects.filter(section=section, status='Active')
        if existing_only:
            existing_ids = Result.objects.filter(subject=subject, term=term, student__section=section) \
                .values_list('student_id', flat=True)
            targets = targets.filter(id__in=existing_ids)
        for student in targets:
            component_values = {
                c.id: int(request.POST.get(f'comp_{c.id}_{student.pk}') or 0) for c in components
            }
            exam = int(request.POST.get(f'exam_{student.pk}') or 0)
            save_result_scores(student, subject, term, request.user, exam, component_values)
        messages.success(request, f'Results saved for {subject} — {section}.')

    rows = []
    if section and subject and term:
        base_qs = Result.objects.filter(subject=subject, term=term, student__section=section) \
            .select_related('student').prefetch_related('component_scores')
        existing = {r.student_id: r for r in base_qs}
        if existing_only:
            student_list = [r.student for r in base_qs.order_by('student__last_name', 'student__first_name')]
        else:
            student_list = list(Student.objects.filter(section=section, status='Active')
                                 .order_by('last_name', 'first_name'))
        for student in student_list:
            r = existing.get(student.id)
            comp_values = {cs.component_id: cs.value for cs in r.component_scores.all()} if r else {}
            rows.append({
                'student': student, 'comp_values': comp_values,
                'exam': r.exam if r else '', 'total': r.total if r else 0, 'grade': r.grade if r else '',
            })

    return render(request, template_name, {
        **sel, 'rows': rows, 'components': components, 'active_nav': active_nav,
        'ca_max_total': sum(c.max_score for c in components),
        'grade_boundaries': GradeBoundary.objects.all(),
    })


@staff_required
def enter_results(request):
    """All active students in the class — for first-time entry. Shows a
    blank row for anyone without a result yet."""
    return _results_grid(request, existing_only=False, template_name='results/entry.html', active_nav='results_entry')


@staff_required
def update_results(request):
    """Only students who already have a result for this subject/term — for
    correcting existing scores, not entering new ones."""
    return _results_grid(request, existing_only=True, template_name='results/update.html', active_nav='results_update')


def _report_card_context(student, term):
    """Shared by the HTML view and the PDF export (both single and bulk)
    so they can never drift apart."""
    results = Result.objects.filter(student=student, term=term) \
        .select_related('subject').prefetch_related('component_scores')
    total = sum(r.total for r in results)
    average = round(total / results.count(), 1) if results else 0
    attendance_qs = student.attendance_records.filter(term=term)
    present = attendance_qs.filter(status='Present').count()
    attendance_rate = round(present / attendance_qs.count() * 100) if attendance_qs else 0
    position, class_size = student_position(student, term)

    return {
        'student': student, 'term': term, 'results': results, 'total': total, 'average': average,
        'overall_grade': GradeBoundary.for_score(average), 'attendance_rate': attendance_rate,
        'position': position, 'class_size': class_size, 'today': timezone.localdate(),
        'components': ScoreComponent.objects.order_by('order'),
    }


def _can_view_report_card(user, student):
    if user.role == 'parent':
        return bool(student.guardian and student.guardian.user_id == user.id)
    if user.role == 'student':
        return student.user_id == user.id
    return True  # admin, teacher


@role_required('admin', 'teacher', 'parent', 'student')
def report_card(request, student_id, term_id):
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(Term, pk=term_id)

    if not _can_view_report_card(request.user, student):
        messages.error(request, 'You do not have permission to view that report card.')
        return render(request, 'results/report_card.html', {'forbidden': True})

    return render(request, 'results/report_card.html', _report_card_context(student, term))


@role_required('admin', 'teacher', 'parent', 'student')
def report_card_pdf(request, student_id, term_id):
    from django.http import HttpResponse
    from results.pdf import render_report_card_pdf

    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(Term, pk=term_id)

    if not _can_view_report_card(request.user, student):
        messages.error(request, 'You do not have permission to view that report card.')
        return redirect('portal:home')

    pdf_bytes = render_report_card_pdf(student, term, request)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"{student.admission_number}-{term.session.name.replace('/', '-')}-{term.name}-report-card.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@staff_required
def broadsheet(request):
    """Class result sheet — every student in a section against every
    subject, with running average and class position. Ported/adapted from
    giia's display_class_results_summary.html pattern. This is a teacher/
    admin-facing SUMMARY SHEET, not a student-facing report card — the
    Report Cards page (below) is the individual-student presentation."""
    sections = sections_for_user(request.user)
    sel = _resolve_selectors(request, sections)
    section, term = sel['section'], sel['term']

    board = class_broadsheet(section, term) if section and term else None

    return render(request, 'results/broadsheet.html', {
        **sel, 'board': board, 'active_nav': 'results_broadsheet',
    })


@staff_required
def report_cards(request):
    """Landing page for the individual report-card workflow: pick a
    session/term/class, then a student — a name roster for navigation, not
    a scores table (the actual result is always presented one student at a
    time, via report_card/report_card_pdf below)."""
    sections = sections_for_user(request.user)
    sel = _resolve_selectors(request, sections)
    section, term = sel['section'], sel['term']

    students = Student.objects.filter(section=section, status='Active').order_by('last_name', 'first_name') \
        if section else Student.objects.none()

    return render(request, 'results/report_cards.html', {
        **sel, 'students': students, 'active_nav': 'results_report_cards',
    })


@staff_required
def class_results_pdf(request):
    """Every active student's report card in the class, combined into a
    single PDF — one page-section per student (see results/pdf.py)."""
    from django.http import Http404, HttpResponse

    from results.pdf import render_class_report_cards_pdf

    sections = sections_for_user(request.user)
    section = _get_by_pk(sections, request.GET.get('section_id'))
    term = _get_by_pk(Term.objects.all(), request.GET.get('term_id')) or Term.get_current()
    if not section or not term:
        raise Http404('Class or term not found.')

    pdf_bytes = render_class_report_cards_pdf(section, term, request)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"{section}-{term.session.name}-{term.name}-report-cards.pdf".replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@staff_required
def download_result_template(request):
    """Excel template for the currently selected session/term/class/subject
    on the Enter Results or Update Results page (existing_only=1)."""
    from django.http import HttpResponse

    from results.excel import build_result_template

    sections = sections_for_user(request.user)
    section = _get_by_pk(sections, request.GET.get('section_id'))
    subject = _get_by_pk(Subject.objects.all(), request.GET.get('subject_id'))
    term = _get_by_pk(Term.objects.all(), request.GET.get('term_id'))
    existing_only = request.GET.get('existing_only') == '1'
    return_to = request.GET.get('return_to') or 'entry'
    if not (section and subject and term):
        messages.error(request, 'Select a session, term, class, and subject first.')
        return redirect(f'results:{return_to}')

    wb = build_result_template(section, subject, term, existing_only=existing_only)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{section}-{subject.name}-{term}-results-template.xlsx".replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@staff_required
def upload_results(request):
    """Bulk-apply scores from an uploaded Excel file — same session/term/
    class/subject scoping as manual entry, matched by admission number."""
    from results.excel import apply_result_upload

    sections = sections_for_user(request.user)
    section = _get_by_pk(sections, request.POST.get('section_id'))
    subject = _get_by_pk(Subject.objects.all(), request.POST.get('subject_id'))
    term = _get_by_pk(Term.objects.all(), request.POST.get('term_id'))
    existing_only = request.POST.get('existing_only') == '1'
    return_to = request.POST.get('return_to') or 'entry'
    excel_file = request.FILES.get('excel_file')

    if not (section and subject and term and excel_file):
        messages.error(request, 'Select a session, term, class, subject, and a file to upload.')
        return redirect(f'results:{return_to}')

    outcome = apply_result_upload(excel_file, section, subject, term, request.user, existing_only=existing_only)
    if outcome.updated:
        messages.success(request, f'{outcome.updated} result(s) updated from the uploaded file.')
    for error in outcome.errors[:10]:
        messages.warning(request, error)
    if len(outcome.errors) > 10:
        messages.warning(request, f'...and {len(outcome.errors) - 10} more row(s) with issues.')
    if not outcome.updated and not outcome.errors:
        messages.info(request, 'No rows with scores were found in that file.')

    url = reverse(f'results:{return_to}')
    return redirect(f"{url}?session_id={term.session_id}&term_id={term.id}&section_id={section.pk}&subject_id={subject.pk}")
