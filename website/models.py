from decimal import Decimal

from django.db import models


class SchoolSettings(models.Model):
    """
    Single admin-editable source of truth for the school's identity, contact
    details, bank account, current session, and the current application fee.

    Deliberately a "solo" model (always pk=1, use SchoolSettings.get_solo())
    rather than hardcoded template constants, so the school can correct its
    own contact info or bump the application fee from the admin site without
    a code change or deploy.

    IMPORTANT: `application_fee` here is the *current* fee. Application
    invoices copy this value onto themselves at creation time (a snapshot,
    not a live reference) — see admissions.models.ApplicationInvoice — so
    changing it here only affects invoices generated *after* the change.
    """

    name = models.CharField(max_length=200, default='Glittering Field Academy')
    tagline = models.CharField(max_length=200, default='Academics and Morality')
    slogan = models.CharField(max_length=200, default='Raising Leaders, Building Future')

    address = models.CharField(
        max_length=255,
        default='No 5 Yarima Dalhatu Crescent, Berger Paint off Chaza Road, Suleja, Niger State',
    )
    email = models.EmailField(default='gfasuleja@gmail.com')
    # Comma-separated — kept as one editable field rather than a related model;
    # split via the `phone_list` property for display.
    phone_numbers = models.CharField(
        max_length=255,
        default='08074339109, 08117436216, 07037785655',
        help_text='Comma-separated list of phone numbers.',
    )
    approvals = models.CharField(
        max_length=255,
        default='WAEC, NECO, NBAIS',
        help_text='Comma-separated list of examination-body approvals.',
    )
    logo = models.ImageField(upload_to='school/', blank=True, null=True)

    bank_name = models.CharField(max_length=100, default='Jaiz Bank')
    bank_account_number = models.CharField(max_length=20, default='0015162724')
    bank_account_name = models.CharField(max_length=200, default='Glittering Field Academy')

    current_session = models.CharField(max_length=20, default='2025/2026')
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2000.00'))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'School Settings'
        verbose_name_plural = 'School Settings'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton — never actually delete

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def phone_list(self):
        return [p.strip() for p in self.phone_numbers.split(',') if p.strip()]

    @property
    def approval_list(self):
        return [a.strip() for a in self.approvals.split(',') if a.strip()]


class PageSection(models.Model):
    """
    One named block of intro/body copy on a public page — the "Welcome"
    paragraph on the homepage, the "Who We Are" text on About, etc. Keyed
    by a fixed `key` the templates already know how to ask for
    (see website/content.py::get_section), so admins editing copy in the
    Superadmin Console can never break a page by renaming/deleting a
    section a template depends on — only the text itself changes.
    """

    key = models.SlugField(max_length=60, unique=True, editable=False)
    page = models.CharField(max_length=20, help_text='Which public page this appears on — for grouping in the console.')
    label = models.CharField(max_length=150, help_text='Human-readable name shown in the console, e.g. "Homepage — Welcome intro".')
    eyebrow = models.CharField(max_length=100, blank=True)
    heading = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, help_text='One paragraph per line.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'label']

    def __str__(self):
        return self.label

    @property
    def paragraphs(self):
        return [p.strip() for p in self.body.splitlines() if p.strip()]


class ContentBlock(models.Model):
    """
    One card in a repeating icon+title+description grid — "Why Choose Us",
    "Mission/Vision/Values", "Our Facilities", "Extracurricular Activities",
    etc. Grouped by (page, section) so a template just asks for its group
    and renders whatever's active, in order — adding, reordering, hiding or
    removing a card from the Superadmin Console never touches a template.
    """

    page = models.CharField(max_length=20)
    section = models.CharField(max_length=40, help_text='Groups cards within a page, e.g. "why_choose_us", "facilities".')
    icon = models.CharField(max_length=60, default='fa-solid fa-star', help_text='Font Awesome class, e.g. "fa-solid fa-book".')
    title = models.CharField(max_length=150)
    description = models.CharField(max_length=300, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['page', 'section', 'order', 'id']

    def __str__(self):
        return f'{self.title} ({self.page} / {self.section})'


class ContactMessage(models.Model):
    """Submissions from the public Contact page — real persistence, not a fake toast."""

    SUBJECT_CHOICES = [
        ('general', 'General Enquiry'),
        ('admissions', 'Admissions'),
        ('fees', 'Fees'),
        ('facilities', 'Facilities'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.get_subject_display()}"
