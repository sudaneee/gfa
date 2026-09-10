from decimal import Decimal, InvalidOperation

from django import forms

from accounts.models import User
from staff.models import Teacher


class ManualPaymentRegistrationForm(forms.Form):
    """
    Admin-side bridge for someone who paid the application fee by bank
    transfer instead of ZainPay (see SchoolSettings.manual_payment_registration_enabled
    — a temporary feature, meant to be switched off once this stops
    happening). Admin sets the username/password directly rather than the
    parent choosing their own, since the admin is creating this account on
    their behalf, not the parent registering themselves.
    """

    full_name = forms.CharField(label='Parent/Guardian Full Name', max_length=150)
    email = forms.EmailField(label='Email Address')
    phone = forms.CharField(label='Phone Number', max_length=20)
    username = forms.CharField(label='Username', max_length=150, help_text='What they will log in with.')
    password = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=8)
    amount = forms.CharField(label='Amount Paid (₦)')
    # Set server-side once a lookup by email/phone finds more than one
    # unclaimed application — the admin then picks which one this payment
    # is for instead of guessing.
    application_id = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def clean_amount(self):
        raw = self.cleaned_data['amount'].replace(',', '').strip()
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            raise forms.ValidationError('Enter a valid amount.')
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class TeacherCreateForm(forms.ModelForm):
    """
    One page, one save — creates the Teacher record AND their login
    together, instead of creating a teacher then separately having to go
    create+link a User account for them afterwards (the generic console
    form has no field for Teacher.user at all, by design — this dedicated
    form exists specifically to fill that gap).
    """

    username = forms.CharField(label='Username', max_length=150, help_text='What they will log in with.')
    password = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=8)
    send_login_email = forms.BooleanField(label='Email them their login details', required=False, initial=True)

    class Meta:
        model = Teacher
        fields = [
            'first_name', 'last_name', 'gender', 'department', 'qualification',
            'phone', 'email', 'employment_date', 'status', 'subjects', 'sections',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Teacher profile first, login credentials last — don't rely on
        # however ModelForm happens to merge declared vs. Meta fields.
        self.order_fields([
            'first_name', 'last_name', 'gender', 'department', 'qualification',
            'phone', 'email', 'employment_date', 'status', 'subjects', 'sections',
            'username', 'password', 'send_login_email',
        ])

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if not email:
            raise forms.ValidationError('An email is needed to send login details, and as their account email.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already exists for this email.')
        return email

    def save(self, commit=True):
        teacher = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data['username'], email=self.cleaned_data['email'],
            password=self.cleaned_data['password'], role='teacher',
            first_name=self.cleaned_data['first_name'], last_name=self.cleaned_data['last_name'],
        )
        teacher.user = user
        if commit:
            teacher.save()
            self.save_m2m()
        return teacher
