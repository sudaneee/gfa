from django import forms

from admissions.models import Application


class ApplicantInfoForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'first_name', 'middle_name', 'last_name', 'date_of_birth',
            'gender', 'nationality', 'state_of_origin', 'lga',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'nationality': forms.TextInput(attrs={'value': 'Nigerian'}),
        }


class GuardianInfoForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['parent_name', 'relationship', 'phone', 'email', 'address', 'occupation']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}


class AcademicInfoForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['applying_for', 'previous_school', 'previous_class', 'previous_performance']


class DocumentsForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['passport_photo', 'birth_certificate', 'previous_result', 'other_document']

    def clean(self):
        cleaned = super().clean()
        # Required on first submission, but don't force re-upload if the
        # applicant already attached one and is just revisiting this step.
        for required in ('passport_photo', 'birth_certificate'):
            has_new = cleaned.get(required)
            has_existing = self.instance and getattr(self.instance, required, None)
            if not has_new and not has_existing:
                self.add_error(required, 'This document is required.')
        return cleaned


class TrackApplicationForm(forms.Form):
    application_number = forms.CharField(label='Application Number', max_length=20)
