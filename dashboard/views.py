# dashboard/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from products.models import *
from .forms import *
from django.forms import modelformset_factory
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from django.db.models import Q



@login_required
def vendor_dashboard(request):
    if not request.user.is_vendor:
        return redirect('become_vendor')

    products = Product.objects.filter(vendor=request.user)

    # Search & filtering params
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')

    if search_query:
        products = products.filter(name__icontains=search_query)

    if category_filter:
        products = products.filter(categories__id=category_filter)

    products = products.distinct()

    # Pagination
    paginator = Paginator(products, 15)  # 15 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Categories for filter dropdown
    from products.models import Category
    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': categories,
    }
    return render(request, 'dashboard/vendor_dashboard.html', context)


@login_required
def add_product(request):
    if not request.user.is_vendor:
        return redirect('vendor_dashboard')  # or some "become vendor" page

    ImageFormSet = modelformset_factory(ProductImage, form=ProductImageForm, extra=3, can_delete=True)
    VariationFormSet = modelformset_factory(ProductVariation, form=ProductVariationForm, extra=3, can_delete=True)

    if request.method == 'POST':
        product_form = ProductForm(request.POST)
        image_formset = ImageFormSet(request.POST, request.FILES, queryset=ProductImage.objects.none())
        variation_formset = VariationFormSet(request.POST, queryset=ProductVariation.objects.none())

        if product_form.is_valid() and image_formset.is_valid() and variation_formset.is_valid():
            product = product_form.save(commit=False)
            product.vendor = request.user
            product.save()
            product_form.save_m2m()

            for form in image_formset.cleaned_data:
                if form and not form.get('DELETE', False):
                    image = form.get('image')
                    if image:
                        ProductImage.objects.create(product=product, image=image)

            for form in variation_formset.cleaned_data:
                if form and not form.get('DELETE', False):
                    variation = ProductVariation(
                        product=product,
                        price=form.get('price'),
                        stock_quantity=form.get('stock_quantity'),
                    )
                    variation.save()
                    attribute_values = form.get('attribute_values')
                    if attribute_values:
                        variation.attribute_values.set(attribute_values)
                    variation.save()

            return redirect('vendor_dashboard')
    else:
        product_form = ProductForm()
        image_formset = ImageFormSet(queryset=ProductImage.objects.none())
        variation_formset = VariationFormSet(queryset=ProductVariation.objects.none())

    categories = list(Category.objects.values('id', 'name'))
    attribute_values_qs = AttributeValue.objects.select_related('attribute').all()
    attribute_values = [
        {'id': av.id, 'display': f'{av.attribute.name}: {av.value}'}
        for av in attribute_values_qs
    ]
    context = {
        'product_form': product_form,
        'image_formset': image_formset,
        'variation_formset': variation_formset,
        'categories': json.dumps(categories, cls=DjangoJSONEncoder),
        'attribute_values': json.dumps(attribute_values, cls=DjangoJSONEncoder),
    }
    return render(request, 'dashboard/add_product.html', context)

@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    categories_list = list(Category.objects.values('id', 'name'))
    attribute_values_qs = AttributeValue.objects.select_related('attribute').all()
    attribute_values = [
        {'id': av.id, 'display': f'{av.attribute.name}: {av.value}'}
        for av in attribute_values_qs
    ]

    if request.method == "POST":
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.regular_price = request.POST.get('regular_price', product.regular_price)
        product.sale_price = request.POST.get('sale_price') or None
        product.stock_quantity = request.POST.get('stock_quantity', product.stock_quantity)
        product.save()

        # Categories
        selected_cat_ids = request.POST.getlist('categories')
        product.categories.set(selected_cat_ids)

        # === Handle new uploaded images ===
        for key in request.FILES:
            if key.startswith('images-'):
                image_file = request.FILES[key]
                ProductImage.objects.create(product=product, image=image_file)

        # === Handle deleted images ===
        deleted_image_ids = request.POST.getlist('deleted_images')
        ProductImage.objects.filter(id__in=deleted_image_ids, product=product).delete()

        # === Handle variations ===
        existing_var_ids = []
        for key in request.POST:
            if key.endswith('-price'):
                prefix = key.rsplit('-', 1)[0]
                index = prefix.split('-')[1]

                var_id_key = f'variations-{index}-id'
                var_id = request.POST.get(var_id_key)

                if var_id:
                    variation = ProductVariation.objects.get(id=var_id, product=product)
                else:
                    variation = ProductVariation(product=product)

                variation.price = request.POST.get(f'variations-{index}-price')
                variation.stock_quantity = request.POST.get(f'variations-{index}-stock_quantity')
                variation.save()

                attr_val_ids = request.POST.getlist(f'variations-{index}-attribute_values')
                variation.attribute_values.set(attr_val_ids)

                existing_var_ids.append(variation.id)

        product.variations.exclude(id__in=existing_var_ids).delete()

        return redirect('vendor_dashboard')

    context = {
        'product': product,
        'categories_list': json.dumps(categories_list, cls=DjangoJSONEncoder),
        'categories': json.dumps([c.id for c in product.categories.all()]),
        'attribute_values': json.dumps(attribute_values, cls=DjangoJSONEncoder),
    }
    return render(request, 'dashboard/edit_product.html', context)



@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, vendor=request.user)
    if request.method == 'POST':
        product.delete()
        return redirect('vendor_dashboard')

    return render(request, 'dashboard/delete_product.html', {'product': product})