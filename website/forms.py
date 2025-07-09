from django import forms
from products.models import Category, ProductVariation

class ProductFilterForm(forms.Form):
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Min Price",
        widget=forms.NumberInput(attrs={'placeholder': 'Min Price'})
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Max Price",
        widget=forms.NumberInput(attrs={'placeholder': 'Max Price'})
    )

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Categories"
    )

    # For Color, Size, Weight, we'll get unique values from ProductVariation
    # In a real application, you might have dedicated models for these attributes
    # or a more robust attribute management system.

    color = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Color"
    )
    size = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Size"
    )
    weight = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Weight"
    )

    # Group Name from Category
    group_name = forms.MultipleChoiceField(
        choices=[], # Will be populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Group Name"
    )

    # Parent Category (top-level categories)
    parent_category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(parent__isnull=True).order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Parent Categories"
    )

    # Child Category, Grand Child, etc. - These would typically be handled dynamically
    # based on selected parent categories or by showing a flat list of all categories.
    # For simplicity, we'll just use the 'categories' field for all levels for now.
    # If you need specific nested filtering, you'd likely use JavaScript to update options
    # based on parent selections.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate choices for color, size, weight from existing product variations
        unique_colors = ProductVariation.objects.values_list('color', flat=True).distinct().exclude(color__isnull=True).exclude(color__exact='').order_by('color')
        self.fields['color'].choices = [(c, c) for c in unique_colors]

        unique_sizes = ProductVariation.objects.values_list('size', flat=True).distinct().exclude(size__isnull=True).exclude(size__exact='').order_by('size')
        self.fields['size'].choices = [(s, s) for s in unique_sizes]

        unique_weights = ProductVariation.objects.values_list('weight', flat=True).distinct().exclude(weight__isnull=True).exclude(weight__exact='').order_by('weight')
        self.fields['weight'].choices = [(w, w) for w in unique_weights]

        # Populate choices for group_name from existing categories
        unique_group_names = Category.objects.values_list('group_name', flat=True).distinct().exclude(group_name__isnull=True).exclude(group_name__exact='').order_by('group_name')
        self.fields['group_name'].choices = [(g, g) for g in unique_group_names]