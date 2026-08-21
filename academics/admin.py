from django.contrib import admin

from academics.models import AcademicSession, FeeBand, SchoolClass, Section, Subject, Term


class TermInline(admin.TabularInline):
    model = Term
    extra = 1


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current', 'start_date', 'end_date')
    list_filter = ('is_current',)
    inlines = [TermInline]


@admin.register(FeeBand)
class FeeBandAdmin(admin.ModelAdmin):
    list_display = ('name',)


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'fee_band', 'order')
    list_filter = ('level', 'fee_band')
    inlines = [SectionInline]
    ordering = ('order',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_filter = ('level',)
    search_fields = ('name',)
