from decimal import Decimal, InvalidOperation

from django import forms

from accounts.models import User


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
