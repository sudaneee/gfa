from django.contrib import admin

from admissions.models import Application, ApplicationInvoice, ApplicationPayment, ApplicationStatusLog


class StatusLogInline(admin.TabularInline):
    model = ApplicationStatusLog
    extra = 0
    readonly_fields = ('stage', 'note', 'created_at')
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = ApplicationPayment
    extra = 0
    readonly_fields = ('reference', 'amount', 'gateway', 'status', 'receipt_number', 'paid_at')
    can_delete = False


class InvoiceInline(admin.StackedInline):
    model = ApplicationInvoice
    extra = 0
    readonly_fields = ('invoice_number', 'amount', 'status', 'generated_at')
    can_delete = False


def _make_status_action(status_value, label):
    def action(modeladmin, request, queryset):
        count = 0
        for application in queryset:
            application.set_status(status_value, note=f'Marked {label} by {request.user}.', user=request.user)
            count += 1
        modeladmin.message_user(request, f'{count} application(s) marked as {label}.')
    action.__name__ = f'mark_{status_value}'
    action.short_description = f'Mark selected as {label}'
    return action


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'application_number', 'full_name', 'gender', 'applying_for',
        'parent_name', 'phone', 'status', 'is_submitted', 'submitted_at',
    )
    list_filter = ('status', 'applying_for', 'is_submitted', 'gender')
    search_fields = ('application_number', 'first_name', 'last_name', 'parent_name', 'phone', 'email')
    readonly_fields = ('application_number', 'created_at', 'submitted_at')
    inlines = [InvoiceInline, StatusLogInline]
    actions = [
        _make_status_action('under_review', 'Under Review'),
        _make_status_action('shortlisted', 'Shortlisted'),
        _make_status_action('interview', 'Interview'),
        _make_status_action('approved', 'Approved'),
        _make_status_action('rejected', 'Rejected'),
        _make_status_action('admitted', 'Admitted'),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_submitted=True)


@admin.register(ApplicationInvoice)
class ApplicationInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'application', 'amount', 'amount_paid', 'balance', 'status', 'generated_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'application__application_number', 'application__first_name', 'application__last_name')
    inlines = [PaymentInline]


@admin.register(ApplicationPayment)
class ApplicationPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'invoice', 'amount', 'gateway', 'status', 'receipt_number', 'paid_at')
    list_filter = ('gateway', 'status')
    search_fields = ('reference', 'gateway_reference', 'receipt_number')

    def save_model(self, request, obj, form, change):
        """
        Manually-recorded payments (e.g. the Jaiz Bank transfer channel) skip
        the ZainPay verify flow entirely. stamp_payment_success_fields/
        sync_invoice_status live in payments/services.py (shared with
        finance.admin.PaymentAdmin and the Superadmin Console) so this
        exact logic is defined in exactly one place.
        """
        from payments.services import stamp_payment_success_fields, sync_invoice_status

        if obj.status == 'success':
            stamp_payment_success_fields(obj, request.user)
        super().save_model(request, obj, form, change)
        sync_invoice_status(obj.invoice)
