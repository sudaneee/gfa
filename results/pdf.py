"""
PDF export for report cards — single student, or a whole class at once.

Ported from the reference giia project's download_single_result_pdf /
download_all_results_pdf (C:\\Users\\ismai\\OneDrive\\Documents\\GitHub\\giia\\src\\views.py),
same underlying tool (WeasyPrint rendering the existing HTML template — no
separate PDF-only template to maintain, and @media print CSS rules already
in dashboard.css apply automatically since WeasyPrint renders in print mode
by default).

Deliberate deviation from giia here: giia's "download all" is a ZIP of one
PDF per student (one full HTML->PDF render per student). This renders the
whole class ONCE into a single HTML document — each student's report card
wrapped in a `page-break-after: always` container (the same technique giia
itself proves works, in src/display_class_results.html) — producing one
combined PDF with one page-section per student, per what was asked for.
"""

from django.template.loader import render_to_string
from weasyprint import HTML


def render_report_card_pdf(student, term, request) -> bytes:
    from results.views import _report_card_context

    html_string = render_to_string(
        'results/report_card.html', _report_card_context(student, term), request=request,
    )
    return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()


def render_class_report_cards_pdf(section, term, request) -> bytes:
    from results.views import _report_card_context
    from students.models import Student

    students = Student.objects.filter(section=section, status='Active').order_by('last_name', 'first_name')
    contexts = [_report_card_context(student, term) for student in students]
    html_string = render_to_string(
        'results/report_card_bulk.html', {'contexts': contexts}, request=request,
    )
    return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
