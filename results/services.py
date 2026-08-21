"""
Class-wide result aggregation — position ranking and the broadsheet grid.
Adapted from the reference giia project's Result.calculate_position()
(C:\\Users\\ismai\\OneDrive\\Documents\\GitHub\\giia\\src\\models.py), reworked
in two ways:

  - giia ranks per-subject (a student's rank in just Mathematics, say).
    This ranks by each student's overall average across all their subjects
    for the term instead — "Position in Class" on a report card is
    conventionally the whole-term standing, not a per-subject one.
  - giia memoizes into a bare mutable class-level dict (`Result._position_cache`)
    that's never invalidated — stale the moment a result changes after first
    computation, and unbounded across a long process lifetime. Skipped
    entirely here; a class's results comfortably fit in one query, so there's
    nothing worth caching yet.
"""

from academics.models import Subject
from results.models import Result, ResultComponentScore
from students.models import Student


def save_result_scores(student, subject, term, teacher, exam, component_values):
    """The single write path for a result — used by the manual entry/update
    grid POST handler, the Excel importer, and demo-data seeding alike, so
    there is exactly one place that knows how to save a Result.

    component_values: {component_id: int}.
    """
    result, _ = Result.objects.update_or_create(
        student=student, subject=subject, term=term,
        defaults={'exam': exam, 'teacher': teacher},
    )
    for component_id, value in component_values.items():
        ResultComponentScore.objects.update_or_create(
            result=result, component_id=component_id, defaults={'value': value},
        )
    result.recompute()
    return result


def class_broadsheet(section, term):
    """
    Every active student in `section`, their score per subject for `term`,
    and their class position — ranked by average descending, with
    competition ranking for ties (two students tied for 1st both show
    position 1, the next student shows position 3, not 2).
    """
    subjects = list(Subject.objects.filter(level=section.school_class.level))
    students = Student.objects.filter(section=section, status='Active').order_by('last_name', 'first_name')

    results_by_student = {}
    for result in Result.objects.filter(student__section=section, term=term, subject__in=subjects):
        results_by_student.setdefault(result.student_id, {})[result.subject_id] = result

    rows = []
    for student in students:
        subject_results = results_by_student.get(student.id, {})
        scores = [r.total for r in subject_results.values()]
        total = sum(scores)
        average = round(total / len(scores), 1) if scores else 0
        rows.append({
            'student': student, 'results': subject_results, 'total': total,
            'average': average, 'has_results': bool(scores),
        })

    _assign_positions(rows)
    return {'subjects': subjects, 'rows': rows, 'class_size': len(rows)}


def _assign_positions(rows):
    """Competition ranking (1, 2, 2, 4, ...) by average, descending. Rows
    with no results at all are left unranked (position=None) rather than
    dragging the ranking down with a false zero."""
    ranked = sorted((r for r in rows if r['has_results']), key=lambda r: r['average'], reverse=True)
    position, last_average = 0, None
    for i, row in enumerate(ranked, start=1):
        if row['average'] != last_average:
            position = i
        row['position'] = position
        last_average = row['average']
    for row in rows:
        row.setdefault('position', None)


def student_position(student, term):
    """Convenience wrapper for the report card — one student's row out of their section's broadsheet."""
    if not student.section:
        return None, 0
    board = class_broadsheet(student.section, term)
    row = next((r for r in board['rows'] if r['student'].id == student.id), None)
    return (row['position'] if row else None), board['class_size']
