from django.contrib import admin

from results.models import GradeBoundary, Result, ResultComponentScore, ScoreComponent


@admin.register(GradeBoundary)
class GradeBoundaryAdmin(admin.ModelAdmin):
    list_display = ('grade', 'min_score', 'max_score', 'point', 'remark')
    ordering = ('-min_score',)


@admin.register(ScoreComponent)
class ScoreComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_score', 'order')
    ordering = ('order',)


class ResultComponentScoreInline(admin.TabularInline):
    model = ResultComponentScore
    extra = 0


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'exam', 'total', 'grade')
    list_filter = ('term', 'subject')
    search_fields = ('student__first_name', 'student__last_name', 'student__admission_number')
    inlines = [ResultComponentScoreInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.recompute()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model is ResultComponentScore:
            form.instance.recompute()
