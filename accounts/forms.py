from django import forms

from accounts.models import User


class AdminCreateUserForm(forms.ModelForm):
    """Superadmin Console's "Add User" form — a plain ModelForm doesn't
    know how to hash a password, so this handles that one bit by hand
    instead of pulling in Django's full UserCreationForm machinery."""

    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class ApplicantSignupForm(forms.Form):
    """
    The public "create an account to apply" form — a plain Form, not a
    ModelForm, since it spans two models (User + Guardian, see
    accounts.views.applicant_signup) rather than saving straight onto one.
    """

    full_name = forms.CharField(label='Full Name', max_length=150)
    email = forms.EmailField(label='Email Address')
    phone = forms.CharField(label='Phone Number', max_length=20)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists — log in instead.')
        return email
