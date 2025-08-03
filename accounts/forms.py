# accounts/forms.py
from django import forms
from .models import VendorProfile

class VendorRegistrationForm(forms.ModelForm):
    # Make the phone number field explicitly required
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}),
        label='Phone Number'
    )
    
    class Meta:
        model = VendorProfile
        # Exclude fields that are set by the system or admin approval
        exclude = ['status', 'application_date', 'approved_date', 'user']
        
        # Override widgets to use our Tailwind CSS classes
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your Company Name'}),
            'contact_person_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Contact Person Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Company Email'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Full Business Address'}),
            'business_type': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Retail, Wholesale'}),
            'website_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'Optional: Website URL'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional: Tax ID'}),
            'nid': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional: National ID Number'}),
        }
        
        # Override labels for clarity
        labels = {
            'company_name': 'Company Name',
            'contact_person_name': 'Contact Person',
            'email': 'Email Address',
            'address': 'Business Address',
            'business_type': 'Business Type',
            'website_url': 'Website URL',
            'tax_id': 'Tax ID (Optional)',
            'vendor_logo': 'Company Logo (Optional)',
            'nid': 'National ID (Optional)',
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if VendorProfile.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered as a vendor.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        # The form's `required` attribute now handles the "is it empty?" check.
        # This method can now focus on the uniqueness check.
        if VendorProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered as a vendor.")
        return phone_number

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Email or Phone Number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'})
    )
