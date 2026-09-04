"""
Termly invoice generation — the one place that turns a FeeStructure into a
student's Invoice. Everything downstream (payments, receipts, reports) only
ever reads the frozen InvoiceItem rows this creates, never FeeStructure
again, so a later fee change can't retroactively alter a bill already sent.
"""

from academics.models import Term
from finance.models import FeeStructure, Invoice, InvoiceItem
from students.models import Student


class InvoiceGenerationError(Exception):
    pass


def student_category(student) -> str:
    """
    'new' the very first time a student is billed at all, 'continuing' on
    every term after — matches the real fee sheet's "New Students" vs
    "Termly/Continuing Students" pricing.
    """
    return 'continuing' if Invoice.objects.filter(student=student).exists() else 'new'


def generate_invoice(student, term: Term) -> Invoice:
    """
    Idempotent: calling this again for a student/term that already has an
    invoice just returns the existing one untouched (never re-snapshots).
    """
    existing = Invoice.objects.filter(student=student, term=term).first()
    if existing:
        return existing

    fee_band = student.school_class.fee_band
    if not fee_band:
        raise InvoiceGenerationError(f"{student.school_class} has no fee band assigned.")

    category = student_category(student)
    structure = FeeStructure.objects.filter(
        session=term.session, fee_band=fee_band, student_category=category,
    ).prefetch_related('items').first()
    if not structure:
        raise InvoiceGenerationError(
            f"No fee structure for {term.session.name} / {fee_band.name} / {category}."
        )

    invoice = Invoice.objects.create(student=student, term=term, fee_structure=structure)
    InvoiceItem.objects.bulk_create([
        InvoiceItem(invoice=invoice, category=item.category, amount=item.amount)
        for item in structure.items.filter(is_optional=False)
    ])
    structure.lock()
    return invoice


def generate_invoices_for_term(term: Term, students=None) -> dict:
    """Batch-generate invoices for a term. Returns a summary for the admin UI."""
    students = students if students is not None else Student.objects.filter(status='Active')
    created, skipped, errors = 0, 0, []

    for student in students:
        if Invoice.objects.filter(student=student, term=term).exists():
            skipped += 1
            continue
        try:
            generate_invoice(student, term)
            created += 1
        except InvoiceGenerationError as exc:
            errors.append(f"{student}: {exc}")

    return {'created': created, 'skipped': skipped, 'errors': errors}
