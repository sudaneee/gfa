from django.contrib import admin

from students.models import Guardian, Student


def generate_current_term_invoices(modeladmin, request, queryset):
    from academics.models import Term
    from finance.services import generate_invoices_for_term

    term = Term.get_current()
    if not term:
        modeladmin.message_user(request, 'No current term is set.', level='error')
        return

    summary = generate_invoices_for_term(term, students=queryset)
    for error in summary['errors']:
        modeladmin.message_user(request, error, level='warning')
    modeladmin.message_user(
        request,
        f"{term}: {summary['created']} invoice(s) created, "
        f"{summary['skipped']} already existed, {len(summary['errors'])} error(s).",
    )


generate_current_term_invoices.short_description = 'Generate current-term fee invoice for selected students'


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('name', 'relationship', 'phone', 'email')
    search_fields = ('name', 'phone', 'email')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'full_name', 'gender', 'school_class', 'section', 'guardian', 'status')
    list_filter = ('school_class', 'status', 'gender')
    search_fields = ('admission_number', 'first_name', 'last_name')
    autocomplete_fields = ['guardian']
    actions = [generate_current_term_invoices]
