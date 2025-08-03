from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import modelformset_factory
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Count, Q
from .forms import VendorProductForm, VendorProductImageForm, VendorProductVariationForm, VariationFormSet
from products.models import *
from accounts.models import VendorProfile
from .forms import VendorProfileForm
import os
import re 
from decimal import Decimal
from .forms import VendorProductForm, VendorProductImageForm, VariationFormSet  # New: import forms




@login_required
def vendor_dashboard(request):
    """
    Vendor dashboard to display their submitted product applications.
    Allows for searching, filtering by status, and provides a status summary.
    """
    # Start with all products for the current vendor
    vendor_products_qs = VendorProduct.objects.filter(vendor=request.user)

    # Search & filtering params
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    # Apply search filter if a query is present
    if search_query:
        vendor_products_qs = vendor_products_qs.filter(name__icontains=search_query)

    # Apply status filter if one is selected
    if status_filter:
        vendor_products_qs = vendor_products_qs.filter(status=status_filter)

    # Get a count of all product statuses for the current vendor
    status_counts = VendorProduct.objects.filter(vendor=request.user).aggregate(
        pending_count=Count('pk', filter=Q(status=VendorProduct.STATUS_PENDING)),
        approved_count=Count('pk', filter=Q(status=VendorProduct.STATUS_APPROVED)),
        rejected_count=Count('pk', filter=Q(status=VendorProduct.STATUS_REJECTED)),
    )
    
    # Order the queryset for display
    vendor_products_qs = vendor_products_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(vendor_products_qs, 15)  # 15 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_counts': status_counts,
    }
    return render(request, 'dashboard/vendor_dashboard.html', context)


@login_required
def vendor_add_product(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                short_description = request.POST.get('short_description')
                product_type = request.POST.get('product_type')
                
                regular_price_str = request.POST.get('regular_price')
                sale_price_str = request.POST.get('sale_price')
                vendor_price_str = request.POST.get('vendor_price')
                stock_quantity_str = request.POST.get('stock_quantity')

                if not name:
                    messages.error(request, "Product name is required.")
                    return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})

                try:
                    regular_price = Decimal(regular_price_str) if regular_price_str else None
                    sale_price = Decimal(sale_price_str) if sale_price_str else None
                    vendor_price = Decimal(vendor_price_str) if vendor_price_str else None
                    stock_quantity = int(stock_quantity_str) if stock_quantity_str else 0

                    for price in [regular_price, sale_price, vendor_price]:
                        if price is not None and price < 0:
                            messages.error(request, "Prices cannot be negative.")
                            return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})
                    if stock_quantity < 0:
                        messages.error(request, "Stock quantity cannot be negative.")
                        return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})
                except (ValueError, TypeError):
                    messages.error(request, "Please enter valid numbers for price and stock.")
                    return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})

                vendor_product = VendorProduct.objects.create(
                    vendor=request.user,
                    name=name,
                    short_description=short_description,
                    description=description,
                    product_type=product_type,
                    regular_price=regular_price,
                    sale_price=sale_price,
                    vendor_price=vendor_price,
                    stock_quantity=stock_quantity,
                    is_active=request.POST.get('is_active') == 'on',
                    is_featured=request.POST.get('is_featured') == 'on',
                    seo_title=request.POST.get('seo_title'),
                    meta_description=request.POST.get('meta_description'),
                    status=VendorProduct.STATUS_PENDING,
                )

                selected_categories_ids = request.POST.getlist('categories')
                vendor_product.categories.set(selected_categories_ids)

                images = request.FILES.getlist('images')
                if images:
                    for i, image_file in enumerate(images):
                        is_featured = (i == 0)
                        VendorProductImage.objects.create(
                            product=vendor_product,
                            image=image_file,
                            alt_text=f"Image of {name} - {i+1}",
                            is_featured=is_featured,
                            order=i
                        )

                for i in range(5):
                    size = request.POST.get(f'variation_size_{i}')
                    color = request.POST.get(f'variation_color_{i}')
                    weight = request.POST.get(f'variation_weight_{i}')
                    price_str = request.POST.get(f'variation_price_{i}')
                    stock_str = request.POST.get(f'variation_stock_{i}')

                    if size or color or weight:
                        try:
                            variation_price = Decimal(price_str) if price_str else None
                            variation_stock = int(stock_str) if stock_str else 0
                            
                            VendorProductVariation.objects.create(
                                product=vendor_product,
                                size=size,
                                color=color,
                                weight=weight,
                                price=variation_price,
                                stock=variation_stock
                            )
                        except (ValueError, TypeError):
                            messages.warning(request, f"Skipped variation {i+1} due to invalid number format.")

            messages.success(request, f"Product '{vendor_product.name}' has been successfully added and is awaiting approval.")
            return redirect('dashboard:vendor_dashboard')

        except Exception as e:
            messages.error(request, f"An error occurred while adding the product: {e}")
            return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})

    context = {
        'categories': categories,
        'product_types': VendorProduct.PRODUCT_TYPE_CHOICES,
    }
    return render(request, 'dashboard/vendor_add_product.html', context)

def get_number_or_default(value_str, default=None, is_int=False):
    if value_str:
        try:
            if is_int:
                return int(value_str)
            else:
                return Decimal(value_str)
        except (ValueError, TypeError):
            return default
    return default

@login_required
def vendor_edit_product(request, product_id):
    product = get_object_or_404(VendorProduct, id=product_id, vendor=request.user)
    categories = Category.objects.all()

    if product.status == VendorProduct.STATUS_APPROVED:
        messages.warning(request, "You cannot edit an approved product.")
        return redirect('dashboard:vendor_product', pk=product.pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # --- 1. Update main product fields ---
                product.name = request.POST.get('name')
                product.description = request.POST.get('description')
                product.short_description = request.POST.get('short_description')
                product.product_type = request.POST.get('product_type')
                product.seo_title = request.POST.get('seo_title')
                product.meta_description = request.POST.get('meta_description')

                product.regular_price = get_number_or_default(request.POST.get('regular_price'), is_int=False)
                product.sale_price = get_number_or_default(request.POST.get('sale_price'), is_int=False)
                product.vendor_price = get_number_or_default(request.POST.get('vendor_price'), is_int=False)
                product.stock_quantity = get_number_or_default(request.POST.get('stock_quantity'), default=0, is_int=True)
                
                product.status = VendorProduct.STATUS_PENDING
                product.save()

                # --- 2. Update Categories (Many-to-Many field) ---
                selected_categories_ids = request.POST.getlist('categories')
                product.categories.set(selected_categories_ids)

                # --- 3. Handle Images: Update, Delete, and Add new ones ---
                submitted_image_ids = set()

                for key, value in request.POST.items():
                    if key.startswith('existing_image_id_'):
                        submitted_image_ids.add(int(value))
                        match = re.search(r'existing_image_id_(\d+)', key)
                        if match:
                            index = match.group(1)
                            image_id = int(value)
                            image_obj = VendorProductImage.objects.get(id=image_id)
                            
                            image_obj.alt_text = request.POST.get(f'existing_image_name_{index}', '')
                            image_obj.order = get_number_or_default(request.POST.get(f'existing_image_order_{index}'), default=0, is_int=True)
                            image_obj.is_featured = (request.POST.get(f'existing_image_featured_{index}') == 'on')
                            image_obj.save()

                existing_image_ids_db = set(product.images.values_list('id', flat=True))
                images_to_delete = existing_image_ids_db.difference(submitted_image_ids)
                VendorProductImage.objects.filter(id__in=images_to_delete).delete()

                new_images = request.FILES.getlist('new_images')
                for i, image_file in enumerate(new_images):
                    image_obj = VendorProductImage.objects.create(
                        product=product,
                        image=image_file,
                        alt_text=request.POST.get(f'new_image_name_{i}', ''),
                        order=get_number_or_default(request.POST.get(f'new_image_order_{i}'), default=0, is_int=True),
                        is_featured=(request.POST.get(f'new_image_featured_{i}') == 'on')
                    )

                # --- 4. Handle Variations: Update, Delete, and Add new ones ---
                submitted_variation_ids = set()

                for key, value in request.POST.items():
                    if key.startswith('existing_variation_id_'):
                        submitted_variation_ids.add(int(value))
                        match = re.search(r'existing_variation_id_(\d+)', key)
                        if match:
                            index = match.group(1)
                            variation_id = int(value)
                            variation_obj = VendorProductVariation.objects.get(id=variation_id)

                            variation_obj.size = request.POST.get(f'existing_variation_size_{index}', '')
                            variation_obj.color = request.POST.get(f'existing_variation_color_{index}', '')
                            variation_obj.weight = request.POST.get(f'existing_variation_weight_{index}', '')
                            variation_obj.price = get_number_or_default(request.POST.get(f'existing_variation_price_{index}'), is_int=False)
                            variation_obj.stock = get_number_or_default(request.POST.get(f'existing_variation_stock_{index}'), default=0, is_int=True)
                            variation_obj.save()
                
                existing_variation_ids_db = set(product.variations.values_list('id', flat=True))
                variations_to_delete = existing_variation_ids_db.difference(submitted_variation_ids)
                VendorProductVariation.objects.filter(id__in=variations_to_delete).delete()

                # --- CORRECTED LOGIC FOR NEW VARIATIONS ---
                # Find all unique indices for new variations, regardless of which fields are filled
                new_variation_indices = set()
                for key in request.POST:
                    if key.startswith('new_variation_'):
                        # Extract the numeric index from the key (e.g., 'new_variation_size_1' -> '1')
                        index_str = key.split('_')[-1]
                        if index_str.isdigit():
                            new_variation_indices.add(int(index_str))

                for i in sorted(list(new_variation_indices)):
                    size = request.POST.get(f'new_variation_size_{i}', '')
                    color = request.POST.get(f'new_variation_color_{i}', '')
                    weight = request.POST.get(f'new_variation_weight_{i}', '')
                    price = request.POST.get(f'new_variation_price_{i}', '')
                    stock = request.POST.get(f'new_variation_stock_{i}', '')
                    
                    # Only create a new variation if at least one field has been filled
                    if size or color or weight or price or stock:
                        VendorProductVariation.objects.create(
                            product=product,
                            size=size,
                            color=color,
                            weight=weight,
                            price=get_number_or_default(price, is_int=False),
                            stock=get_number_or_default(stock, default=0, is_int=True)
                        )
                # --- END OF CORRECTED LOGIC ---

            messages.success(request, f"Product '{product.name}' has been updated and sent for re-approval.")
            return redirect('dashboard:vendor_product', pk=product.pk)

        except Exception as e:
            messages.error(request, f"Error updating product: {e}")
            return render(request, 'dashboard/vendor_edit_product.html', {
                'product': product,
                'categories': categories,
                'product_types': VendorProduct.PRODUCT_TYPE_CHOICES,
            })

    # GET request context
    context = {
        'product': product,
        'categories': categories,
        'product_types': VendorProduct.PRODUCT_TYPE_CHOICES,
    }
    return render(request, 'dashboard/vendor_edit_product.html', context)


@login_required
def delete_product_application(request, pk):
    """
    Allow a vendor to delete their product application (regardless of status).
    """
    vendor_product = get_object_or_404(VendorProduct, pk=pk)

    # Ensure the logged-in user is the owner
    if vendor_product.vendor != request.user:
        messages.error(request, "You do not have permission to delete this product.")
        return redirect('dashboard:vendor_dashboard')

    if request.method == 'POST':
        vendor_product.delete()
        messages.success(request, f"Product '{vendor_product.name}' was deleted successfully.")
        return redirect('dashboard:vendor_dashboard')

    context = {
        'vendor_product': vendor_product
    }
    return render(request, 'dashboard/delete_product_application.html', context)


@login_required
def vendor_product(request, pk):
    """
    Displays a specific product for the logged-in vendor.
    """
    vendor_product = get_object_or_404(VendorProduct, pk=pk, vendor=request.user)

    context = {
        'product': vendor_product,
    }
    return render(request, 'dashboard/vendor_product.html', context)


@login_required
def vendor_profile_edit(request):
    """
    Allows a logged-in vendor to edit their profile.
    """
    try:
        vendor_profile = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        messages.error(request, "You do not have a vendor profile to edit.")
        return redirect('some_other_page') # Redirect to a safe page

    if request.method == 'POST':
        form = VendorProfileForm(request.POST, request.FILES, instance=vendor_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('dashboard:vendor_profile_view') # Redirect back to the same page
    else:
        form = VendorProfileForm(instance=vendor_profile)

    context = {
        'form': form,
    }
    return render(request, 'dashboard/vendor_profile_edit.html', context)

@login_required
def vendor_profile_view(request):
    try:
        vendor_profile = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        messages.error(request, "You do not have a vendor profile.")
        return redirect('some_other_page')
    
    context = {
        'profile': vendor_profile
    }
    return render(request, 'dashboard/vendor_profile_view.html', context)