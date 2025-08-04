from django import forms
from django.forms import modelformset_factory
from django.forms.widgets import ClearableFileInput
from products.models import VendorProduct, VendorProductImage, VendorProductVariation
from accounts.models import CustomUser
from orders.models import VendorOrder

# 1. Create a custom widget that supports multiple files
class MultipleFileInput(forms.FileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        # Ensure the 'multiple' attribute is always set
        self.attrs['multiple'] = True

# 2. Create a custom field that uses the custom widget
class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # The clean method needs to handle a list of files
        single_file = False
        if not data:
            return None # No files uploaded
        if not isinstance(data, list):
            # This handles a single file upload gracefully
            single_file = True
            data = [data]

        cleaned_data = []
        for file in data:
            cleaned_data.append(super().clean(file))
        
        # If it was a single file, return a single file
        if single_file:
            return cleaned_data[0]
            
        return cleaned_data

class VendorProductForm(forms.ModelForm):
    """A form for editing the main VendorProduct fields."""
    class Meta:
        model = VendorProduct
        fields = [
            'name', 'short_description', 'description', 'product_type', 'categories',
            'regular_price', 'sale_price', 'stock_quantity',
            'seo_title', 'meta_description',
        ]
        widgets = {
            'categories': forms.SelectMultiple(),
            'description': forms.Textarea(attrs={'class': 'rich-text-editor'}),
            'short_description': forms.Textarea(attrs={'rows': 3}),
        }

class VendorProductImageForm(forms.Form):
    """A form for adding new images to a product."""
    # 3. Use the new custom field here
    images = MultipleImageField(
        label='Add new images',
        required=False,
    )

class VendorProductVariationForm(forms.ModelForm):
    """A form for a single product variation."""
    class Meta:
        model = VendorProductVariation
        fields = ['size', 'weight', 'color', 'price', 'stock']

VariationFormSet = modelformset_factory(
    VendorProductVariation,
    form=VendorProductVariationForm,
    extra=1,
    can_delete=True,
)

# edit profile 
class VendorProfileForm(forms.ModelForm):
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
        labels = {
            'nid': 'NID/Passport Number',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tailwind_classes = "mt-1 block w-full rounded-md border border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2"

        for name, field in self.fields.items():
            if name != 'vendor_logo':
                if name == 'address':
                    field.widget.attrs.update({'class': f"{tailwind_classes} h-24"})
                else:
                    field.widget.attrs.update({'class': tailwind_classes})

        self.fields['email'].widget.attrs.update({
            'readonly': 'readonly',
            'class': f"{tailwind_classes} bg-gray-100 cursor-not-allowed"
        })
        self.fields['phone_number'].widget.attrs.update({
            'readonly': 'readonly',
            'class': f"{tailwind_classes} bg-gray-100 cursor-not-allowed"
        })


class VendorOrderStatusForm(forms.ModelForm):
    class Meta:
        model = VendorOrder
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=[
                ('processing', 'Processing'),
                ('shipped', 'Shipped'),
                ('delivered', 'Delivered'),
                ('cancelled', 'Cancelled'),
            ], attrs={'class': 'form-select'})
        }