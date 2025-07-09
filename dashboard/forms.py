# dashboard/forms.py
from django import forms
from products.models import Product, ProductImage, ProductVariation, Category # Import Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # Remove 'slug' and 'created_at' as they are auto-generated.
        # 'vendor' will likely be set in the view based on the logged-in user.
        exclude = ['vendor', 'slug', 'created_at', 'updated_at']

    # Use the Category model directly for the queryset
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(), # Corrected: use Category.objects.all()
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Categories" # Add a label for clarity
    )

    # Add custom widgets for better user experience if desired
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Example: Add CSS classes to fields
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['short_description'].widget.attrs.update({'class': 'form-control ckeditor'})
        self.fields['description'].widget.attrs.update({'class': 'form-control ckeditor'})
        self.fields['product_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['regular_price'].widget.attrs.update({'class': 'form-control'})
        self.fields['sale_price'].widget.attrs.update({'class': 'form-control'})
        self.fields['stock_quantity'].widget.attrs.update({'class': 'form-control'})
        self.fields['sku'].widget.attrs.update({'class': 'form-control'})
        self.fields['gtin'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_featured'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['seo_title'].widget.attrs.update({'class': 'form-control'})
        self.fields['meta_description'].widget.attrs.update({'class': 'form-control'})


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'name', 'alt_text', 'is_featured', 'order'] # Added more fields for better control

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['alt_text'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_featured'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['order'].widget.attrs.update({'class': 'form-control'})


class ProductVariationForm(forms.ModelForm):
    # Removed attribute_values as it's no longer in the model
    # Instead, use the direct fields 'size', 'weight', 'color'
    class Meta:
        model = ProductVariation
        fields = ['size', 'weight', 'color', 'price', 'stock'] # Corrected fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['size'].widget.attrs.update({'class': 'form-control'})
        self.fields['weight'].widget.attrs.update({'class': 'form-control'})
        self.fields['color'].widget.attrs.update({'class': 'form-control'})
        self.fields['price'].widget.attrs.update({'class': 'form-control'})
        self.fields['stock'].widget.attrs.update({'class': 'form-control'})