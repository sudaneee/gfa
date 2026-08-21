from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class FeeStructure(models.Model):
    """
    One priced schedule for a (session, fee band, new/continuing) combo —
    e.g. "2025/2026, Junior Secondary, New Student" = ₦79,000 itemized.

    Locked the moment it generates its first Invoice (`is_locked=True`).
    A locked structure's items can no longer be edited in the admin — the
    only way to change fees after that is a new FeeStructure (new session,
    or a deliberate new version), never an in-place edit. This is the
    mechanism behind the plan's "changing fees must never alter a past
    invoice" requirement: Invoice/InvoiceItem below copy amounts out of
    here at generation time and never reference it live again.
    """

    STUDENT_CATEGORY_CHOICES = [('new', 'New Student'), ('continuing', 'Continuing Student')]

    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE, related_name='fee_structures')
    fee_band = models.ForeignKey('academics.FeeBand', on_delete=models.CASCADE, related_name='fee_structures')
    student_category = models.CharField(max_length=12, choices=STUDENT_CATEGORY_CHOICES)
    is_locked = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'fee_band', 'student_category')
        ordering = ['-session__name', 'fee_band__name', 'student_category']
        verbose_name_plural = 'Fee structures'

    def __str__(self):
        return f"{self.session.name} — {self.fee_band.name} — {self.get_student_category_display()}"

    @property
    def total_amount(self):
        """Required total only — matches the PDF's "GRAND TOTAL" row, which
        excludes the optional Jacket line shown separately beneath it."""
        return self.items.filter(is_optional=False).aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    def lock(self):
        if not self.is_locked:
            self.is_locked = True
            self.save(update_fields=['is_locked'])


class FeeStructureItem(models.Model):
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_optional = models.BooleanField(default=False, help_text='e.g. the Jacket line — excluded from auto-generated invoices.')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.category} — ₦{self.amount:,.2f}"


def generate_invoice_number():
    import uuid
    return f"FEE-INV-{timezone.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"


def generate_payment_reference():
    import uuid
    return f"GFA-{uuid.uuid4().hex[:12].upper()}"


class Invoice(models.Model):
    """Termly school fees. Items are a frozen copy — see FeeStructure's docstring."""

    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'), ('partial', 'Partially Paid'), ('paid', 'Paid'), ('waived', 'Waived'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='invoices')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='invoices')
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices',
        help_text='Reference only — amounts below are already frozen and independent of this.',
    )
    invoice_number = models.CharField(max_length=40, unique=True, default=generate_invoice_number, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'term')
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.invoice_number} — {self.student} — {self.term}"

    @property
    def total(self):
        return self.items.aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    @property
    def amount_paid(self):
        return self.payments.filter(status='success').aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    @property
    def balance(self):
        return max(self.total - self.amount_paid, Decimal('0.00'))

    @property
    def is_paid(self):
        return self.total > 0 and self.amount_paid >= self.total


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.category} — ₦{self.amount:,.2f}"


class Payment(models.Model):
    GATEWAY_CHOICES = [('zainpay', 'ZainPay'), ('manual', 'Manual (Bank Transfer)'), ('waiver', 'Waiver')]
    STATUS_CHOICES = [('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('reversed', 'Reversed')]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    reference = models.CharField(max_length=40, unique=True, default=generate_payment_reference)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES, default='zainpay')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    gateway_reference = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_fee_payments',
    )
    receipt_number = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()} (₦{self.amount:,.2f})"
