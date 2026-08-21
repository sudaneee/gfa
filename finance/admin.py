from django.contrib import admin

from finance.models import FeeStructure, FeeStructureItem, Invoice, InvoiceItem, Payment


class FeeStructureItemInline(admin.TabularInline):
    model = FeeStructureItem
    extra = 1

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_locked)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_locked)

    def has_add_permission(self, request, obj=None):
        return not (obj and obj.is_locked)


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('session', 'fee_band', 'student_category', 'total_amount', 'is_locked')
    list_filter = ('session', 'fee_band', 'student_category', 'is_locked')
    readonly_fields = ('is_locked',)
    inlines = [FeeStructureItemInline]

    def get_readonly_fields(self, request, obj=None):
        # Once locked, the (session, fee_band, student_category) identity is
        # also frozen — create a new FeeStructure instead of repurposing this one.
        if obj and obj.is_locked:
            return ('session', 'fee_band', 'student_category', 'is_locked')
        return self.readonly_fields


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ('category', 'amount')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('reference', 'amount', 'gateway', 'status', 'receipt_number', 'paid_at')
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'student', 'term', 'total', 'amount_paid', 'balance', 'status')
    list_filter = ('term', 'status')
    search_fields = ('invoice_number', 'student__first_name', 'student__last_name', 'student__admission_number')
    inlines = [InvoiceItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'invoice', 'amount', 'gateway', 'status', 'receipt_number', 'paid_at')
    list_filter = ('gateway', 'status')
    search_fields = ('reference', 'gateway_reference', 'receipt_number')

    def save_model(self, request, obj, form, change):
        """Manual (bank transfer) payments skip Zainpay verification — mirror
        admissions.admin's same behaviour so the invoice status rolls forward.
        stamp_payment_success_fields/sync_invoice_status live in
        finance/services.py so the Superadmin Console's "Mark Received"
        action shares this exact logic instead of a second copy."""
        from finance.services import stamp_payment_success_fields, sync_invoice_status

        if obj.status == 'success':
            stamp_payment_success_fields(obj, request.user)
        super().save_model(request, obj, form, change)
        sync_invoice_status(obj.invoice)
