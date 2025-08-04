from django import forms
from .models import CustomUser
from django.utils import timezone
from django.utils.crypto import get_random_string

class VendorRegistrationForm(forms.ModelForm):
    company_name = forms.CharField(required=True)
    contact_person_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True)
    address = forms.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = [
            'company_name',
            'contact_person_name',
            'email',
            'phone_number',
            'address',
            'business_type',
            'website_url',
            'tax_id',
            'vendor_logo',
            'nid',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if CustomUser.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("Phone number already exists.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        # username assigned in view, but can set here too if you want
        user.vendor_status = CustomUser.STATUS_PENDING
        user.application_date = timezone.now()
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(label="Email or Username", max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
