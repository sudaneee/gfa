"""
Declarative registry driving the generic CRUD scaffold — one entry per
model that's safe for a plain ModelForm (no side effects beyond a normal
save). Applications/Invoices/Payments/FeeStructure are deliberately NOT
here — they have real business logic (status logs, frozen invoice
snapshots, payment rollups) that a generic form would bypass or corrupt;
see admin_console/views.py's dedicated handlers for those instead.

`list_fields` supports dotted lookups and properties (resolved via
`admin_console.utils.resolve_field`), not just plain model fields.
"""

from dataclasses import dataclass, field


@dataclass
class ManagedModel:
    slug: str
    model: type
    label: str
    singular: str
    icon: str
    category: str
    list_fields: list          # [(attr_path, column_label), ...]
    search_fields: list = field(default_factory=list)   # ORM __icontains lookups
    filter_fields: list = field(default_factory=list)    # [(field_name, label), ...] — choices pulled from the model
    form_fields: list = field(default_factory=list)       # passed to modelform_factory
    can_delete: bool = True
    ordering: str | None = None


def _build_registry():
    from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Subject, Term
    from communication.models import Announcement, Event
    from results.models import GradeBoundary, ScoreComponent
    from staff.models import Teacher
    from students.models import Guardian, Student
    from website.models import ContactMessage, ContentBlock, PageSection

    entries = [
        ManagedModel(
            slug='students', model=Student, label='Students', singular='Student',
            icon='fa-solid fa-user-graduate', category='People',
            list_fields=[('admission_number', 'Admission No.'), ('full_name', 'Name'),
                         ('school_class', 'Class'), ('section', 'Section'), ('status', 'Status')],
            search_fields=['admission_number', 'first_name', 'last_name'],
            filter_fields=[('status', 'Status'), ('school_class', 'Class')],
            form_fields=['first_name', 'last_name', 'gender', 'date_of_birth', 'photo',
                         'school_class', 'section', 'guardian', 'status', 'admission_date'],
        ),
        ManagedModel(
            slug='guardians', model=Guardian, label='Guardians', singular='Guardian',
            icon='fa-solid fa-people-roof', category='People',
            list_fields=[('name', 'Name'), ('relationship', 'Relationship'), ('phone', 'Phone'), ('email', 'Email')],
            search_fields=['name', 'phone', 'email'],
            filter_fields=[('relationship', 'Relationship')],
            form_fields=['name', 'relationship', 'phone', 'email', 'address', 'occupation'],
        ),
        ManagedModel(
            slug='teachers', model=Teacher, label='Teachers', singular='Teacher',
            icon='fa-solid fa-chalkboard-user', category='People',
            list_fields=[('staff_id', 'Staff ID'), ('full_name', 'Name'), ('department', 'Department'), ('status', 'Status')],
            search_fields=['staff_id', 'first_name', 'last_name', 'email'],
            filter_fields=[('status', 'Status'), ('department', 'Department')],
            form_fields=['first_name', 'last_name', 'gender', 'department', 'qualification',
                         'phone', 'email', 'employment_date', 'status', 'subjects', 'sections'],
        ),
        ManagedModel(
            slug='sessions', model=AcademicSession, label='Academic Sessions', singular='Session',
            icon='fa-solid fa-calendar-days', category='Academics',
            list_fields=[('name', 'Session'), ('is_current', 'Current'), ('start_date', 'Start'), ('end_date', 'End')],
            search_fields=['name'],
            form_fields=['name', 'is_current', 'start_date', 'end_date'],
        ),
        ManagedModel(
            slug='terms', model=Term, label='Terms', singular='Term',
            icon='fa-solid fa-calendar-week', category='Academics',
            list_fields=[('session', 'Session'), ('name', 'Term'), ('is_current', 'Current'), ('start_date', 'Start'), ('end_date', 'End')],
            filter_fields=[('session', 'Session'), ('name', 'Term')],
            form_fields=['session', 'name', 'is_current', 'start_date', 'end_date'],
        ),
        ManagedModel(
            slug='classes', model=SchoolClass, label='Classes', singular='Class',
            icon='fa-solid fa-school', category='Academics',
            list_fields=[('name', 'Class'), ('level', 'Level'), ('fee_band', 'Fee Band'), ('order', 'Order')],
            search_fields=['name'],
            filter_fields=[('level', 'Level')],
            form_fields=['name', 'level', 'fee_band', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='sections', model=Section, label='Sections', singular='Section',
            icon='fa-solid fa-people-line', category='Academics',
            list_fields=[('school_class', 'Class'), ('name', 'Section')],
            filter_fields=[('school_class', 'Class')],
            form_fields=['school_class', 'name'],
        ),
        ManagedModel(
            slug='subjects', model=Subject, label='Subjects', singular='Subject',
            icon='fa-solid fa-book', category='Academics',
            list_fields=[('name', 'Subject'), ('level', 'Level')],
            search_fields=['name'],
            filter_fields=[('level', 'Level')],
            form_fields=['name', 'level'],
        ),
        ManagedModel(
            slug='fee-bands', model=FeeBand, label='Fee Bands', singular='Fee Band',
            icon='fa-solid fa-layer-group', category='Academics',
            list_fields=[('name', 'Fee Band')],
            search_fields=['name'],
            form_fields=['name'],
        ),
        ManagedModel(
            slug='announcements', model=Announcement, label='Announcements', singular='Announcement',
            icon='fa-solid fa-bullhorn', category='Communication',
            list_fields=[('title', 'Title'), ('audience', 'Audience'), ('is_published', 'Published'), ('created_at', 'Created')],
            search_fields=['title', 'content'],
            filter_fields=[('audience', 'Audience'), ('is_published', 'Published')],
            form_fields=['title', 'content', 'audience', 'is_published'],
        ),
        ManagedModel(
            slug='events', model=Event, label='Events', singular='Event',
            icon='fa-solid fa-calendar-star', category='Communication',
            list_fields=[('title', 'Title'), ('category', 'Category'), ('date', 'Date')],
            search_fields=['title', 'description'],
            filter_fields=[('category', 'Category')],
            form_fields=['title', 'description', 'category', 'date'],
        ),
        ManagedModel(
            slug='grade-boundaries', model=GradeBoundary, label='Grade Boundaries', singular='Grade Boundary',
            icon='fa-solid fa-ranking-star', category='Results',
            list_fields=[('grade', 'Grade'), ('min_score', 'Min'), ('max_score', 'Max'), ('point', 'Point'), ('remark', 'Remark')],
            form_fields=['grade', 'min_score', 'max_score', 'point', 'remark'],
        ),
        ManagedModel(
            slug='page-sections', model=PageSection, label='Website Page Text', singular='Page Section',
            icon='fa-solid fa-align-left', category='Website',
            list_fields=[('label', 'Section'), ('page', 'Page'), ('heading', 'Heading')],
            search_fields=['label', 'heading', 'body'],
            form_fields=['eyebrow', 'heading', 'body'],
            can_delete=False,  # a fixed set of named slots the templates already reference by key
        ),
        ManagedModel(
            slug='content-blocks', model=ContentBlock, label='Website Content Cards', singular='Content Card',
            icon='fa-solid fa-table-cells', category='Website',
            list_fields=[('page', 'Page'), ('section', 'Section'), ('title', 'Title'), ('order', 'Order'), ('is_active', 'Active')],
            search_fields=['title', 'description', 'page', 'section'],
            form_fields=['page', 'section', 'icon', 'title', 'description', 'order', 'is_active'],
            ordering='order',
        ),
        ManagedModel(
            slug='contact-messages', model=ContactMessage, label='Contact Messages', singular='Contact Message',
            icon='fa-solid fa-envelope-open-text', category='Website',
            list_fields=[('name', 'Name'), ('subject', 'Subject'), ('phone', 'Phone'), ('email', 'Email'),
                         ('is_read', 'Read'), ('created_at', 'Received')],
            search_fields=['name', 'email', 'phone', 'message'],
            filter_fields=[('subject', 'Subject'), ('is_read', 'Read')],
            form_fields=['name', 'phone', 'email', 'subject', 'message', 'is_read'],
        ),
        ManagedModel(
            slug='score-components', model=ScoreComponent, label='Score Components', singular='Score Component',
            icon='fa-solid fa-list-ol', category='Results',
            list_fields=[('name', 'Name'), ('max_score', 'Max Score'), ('order', 'Order')],
            form_fields=['name', 'max_score', 'order'],
            ordering='order',
        ),
    ]
    return {entry.slug: entry for entry in entries}


REGISTRY = _build_registry()


def categories():
    """REGISTRY entries grouped by category, in first-seen order — drives
    both the sidebar nav and a console index page."""
    grouped = {}
    for entry in REGISTRY.values():
        grouped.setdefault(entry.category, []).append(entry)
    return grouped
