from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

# Class → level mapping. Free-standing for now (CharField choices) rather
# than an FK to a SchoolClass model, since the academics app's data model
# doesn't exist yet (a later phase) — swapping this for a real FK later is a
# standard, low-risk migration once that model lands.
CLASS_LEVEL_MAP = {
    'Creche': 'Creche',
    'Pre-Nursery': 'Pre-Nursery',
    'Nursery 1': 'Nursery',
    'Nursery 2': 'Nursery',
    'Primary 1': 'Primary', 'Primary 2': 'Primary', 'Primary 3': 'Primary',
    'Primary 4': 'Primary', 'Primary 5': 'Primary', 'Primary 6': 'Primary',
    'JSS 1': 'Secondary', 'JSS 2': 'Secondary', 'JSS 3': 'Secondary',
    'SSS 1': 'Secondary', 'SSS 2': 'Secondary', 'SSS 3': 'Secondary',
}
APPLYING_FOR_CHOICES = [(name, name) for name in CLASS_LEVEL_MAP]


def generate_application_number():
    """GFA-<year>-<sequence>, matching the frontend prototype's format."""
    year = timezone.localdate().year
    prefix = f"GFA-{year}-"
    last = (
        Application.objects.filter(application_number__startswith=prefix)
        .order_by('-application_number')
        .first()
    )
    next_seq = int(last.application_number.split('-')[-1]) + 1 if last else 101
    return f"{prefix}{next_seq:06d}"


def application_document_path(instance, filename):
    # `instance` is the Application itself here (these FileFields live
    # directly on it), not a related model.
    return f"admissions/{instance.application_number}/{filename}"


def generate_invoice_number():
    import uuid
    # Timestamp for readability/sorting + a uuid suffix so two invoices
    # created within the same second (easily hit in tests, and possible in
    # production under concurrent submissions) never collide.
    return f"APP-INV-{timezone.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"


def generate_payment_reference():
    import uuid
    return f"GFA-{uuid.uuid4().hex[:12].upper()}"


def generate_resume_token():
    import secrets
    return secrets.token_urlsafe(24)


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('admitted', 'Admitted'),
    ]
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    RELATIONSHIP_CHOICES = [('Father', 'Father'), ('Mother', 'Mother'), ('Guardian', 'Guardian')]
    PERFORMANCE_CHOICES = [
        ('Excellent', 'Excellent'), ('Very Good', 'Very Good'), ('Good', 'Good'),
        ('Fair', 'Fair'), ('First time in school', 'First time in school'),
    ]

    application_number = models.CharField(
        max_length=20, unique=True, default=generate_application_number, editable=False,
    )
    # A secret, unguessable companion to application_number (which is
    # sequential and public-facing via the tracking page) — the only thing
    # that lets someone resume editing an in-progress application. Never
    # shown on any page; only ever delivered by email, so continuing an
    # application never depends on the original browser/device/session
    # that started it.
    resume_token = models.CharField(max_length=48, unique=True, default=generate_resume_token, editable=False)

    # Step 1 — Applicant information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=100, default='Nigerian')
    state_of_origin = models.CharField(max_length=100)
    lga = models.CharField(max_length=100, verbose_name='Local Government Area')

    # Step 2 — Parent / guardian information
    parent_name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    occupation = models.CharField(max_length=150, blank=True)

    # Step 3 — Academic information
    applying_for = models.CharField(max_length=20, choices=APPLYING_FOR_CHOICES)
    previous_school = models.CharField(max_length=200, blank=True)
    previous_class = models.CharField(max_length=50, blank=True)
    previous_performance = models.CharField(max_length=30, choices=PERFORMANCE_CHOICES, blank=True)

    # Step 4 — Documents
    passport_photo = models.FileField(upload_to=application_document_path, blank=True, null=True)
    birth_certificate = models.FileField(upload_to=application_document_path, blank=True, null=True)
    previous_result = models.FileField(upload_to=application_document_path, blank=True, null=True)
    other_document = models.FileField(upload_to=application_document_path, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # False while the applicant is still stepping through the wizard (the row
    # exists early so file uploads have somewhere to attach across steps).
    # Only True once they reach the final "Submit" step — admin list views,
    # the tracking page, and the applicant count all filter on this so an
    # abandoned half-filled form never shows up as a real application.
    is_submitted = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application_number} — {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return ' '.join(p for p in [self.first_name, self.middle_name, self.last_name] if p)

    @property
    def level(self):
        return CLASS_LEVEL_MAP.get(self.applying_for, '')

    def set_status(self, new_status, note='', user=None):
        """Change status and drop a timeline entry — used by both the admin
        actions and any future portal review UI, so the two never drift."""
        self.status = new_status
        if user is not None:
            self.reviewed_by = user
        self.save(update_fields=['status', 'reviewed_by'] if user else ['status'])
        self.status_logs.create(stage=new_status, note=note)


class ApplicationStatusLog(models.Model):
    """One row per status change — the tracking page's visual timeline."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_logs')
    stage = models.CharField(max_length=20, choices=Application.STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.application.application_number} → {self.stage}"


class ApplicationInvoice(models.Model):
    """
    The application fee, snapshotted at creation time from
    SchoolSettings.application_fee — never a live lookup, so a later fee
    change never alters an invoice already issued (see the plan's fee
    versioning requirement).
    """

    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=30, unique=True, default=generate_invoice_number, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.invoice_number} — {self.get_status_display()}"

    @property
    def amount_paid(self):
        return self.payments.filter(status='success').aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    @property
    def balance(self):
        return max(self.amount - self.amount_paid, Decimal('0.00'))

    @property
    def is_paid(self):
        return self.amount_paid >= self.amount


class ApplicationPayment(models.Model):
    GATEWAY_CHOICES = [
        ('zainpay', 'ZainPay'),
        ('manual', 'Manual (Bank Transfer)'),
        ('waiver', 'Waiver'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    invoice = models.ForeignKey(ApplicationInvoice, on_delete=models.CASCADE, related_name='payments')
    reference = models.CharField(max_length=40, unique=True, default=generate_payment_reference)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES, default='zainpay')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    gateway_reference = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_application_payments',
    )
    receipt_number = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()} (₦{self.amount:,.2f})"
