from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import modelformset_factory
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from .forms import VendorProductForm, VendorProductImageForm, VendorProductVariationForm, VariationFormSet
from products.models import *
# from accounts.models import VendorProfile
from .forms import VendorProfileForm
import os
import re 
from decimal import Decimal
from .forms import VendorProductForm, VendorProductImageForm, VariationFormSet, VendorOrderStatusForm  # New: import forms
from orders.models import *  # New: import models for orders
from decimal import Decimal, ROUND_HALF_UP
from collections import Counter
from django.utils import timezone
from datetime import datetime
import csv
from django.http import HttpResponse

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


def get_number_or_default(value_str, default=None, is_int=False):
    """Safely converts a string to a number (int or Decimal) or returns a default value."""
    if value_str:
        try:
            if is_int:
                return int(value_str)
            else:
                # Use Decimal for monetary values to avoid floating-point issues
                return Decimal(value_str)
        except (ValueError, TypeError):
            # Fallback to default if conversion fails
            return default
    return default


@login_required
def vendor_add_product(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                short_description = request.POST.get('short_description')
                description = request.POST.get('description')
                product_type = request.POST.get('product_type')
                
                # Use the helper function to safely get and convert values
                regular_price = get_number_or_default(request.POST.get('regular_price'), default=Decimal('0.00'))
                sale_price = get_number_or_default(request.POST.get('sale_price'))
                vendor_price = get_number_or_default(request.POST.get('vendor_price'), default=Decimal('0.00'))
                
                # Fix: Explicitly provide a default value to prevent NOT NULL errors
                admin_commission = get_number_or_default(request.POST.get('admin_commission'), default=Decimal('0.00'))
                
                stock_quantity = get_number_or_default(request.POST.get('stock_quantity'), default=0, is_int=True)

                if not name:
                    messages.error(request, "Product name is required.")
                    return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})

                # You can use a form or more robust validation here, but for this example, we'll keep the direct checks.
                if regular_price is not None and regular_price < 0:
                    messages.error(request, "Regular price cannot be negative.")
                    return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})
                if sale_price is not None and sale_price >= regular_price:
                    messages.error(request, "Sale price must be less than the regular price.")
                    return render(request, 'dashboard/vendor_add_product.html', {'categories': categories})
                if stock_quantity < 0:
                    messages.error(request, "Stock quantity cannot be negative.")
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
                    admin_commission=admin_commission,
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
                        variation_price = get_number_or_default(price_str)
                        variation_stock = get_number_or_default(stock_str, default=0, is_int=True)
                        
                        VendorProductVariation.objects.create(
                            product=vendor_product,
                            size=size,
                            color=color,
                            weight=weight,
                            price=variation_price,
                            stock=variation_stock
                        )

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

@login_required
def vendor_edit_product(request, product_id):
    product = get_object_or_404(VendorProduct, id=product_id, vendor=request.user)
    categories = Category.objects.all()

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

                product.regular_price = get_number_or_default(request.POST.get('regular_price'), default=Decimal('0.00'), is_int=False)
                product.sale_price = get_number_or_default(request.POST.get('sale_price'), default=None, is_int=False)
                product.vendor_price = get_number_or_default(request.POST.get('vendor_price'), default=Decimal('0.00'), is_int=False)
                
                # --- FIX: Provide an explicit default value for admin_commission ---
                product.admin_commission = get_number_or_default(request.POST.get('admin_commission'), default=Decimal('0.00'), is_int=False)
                
                product.stock_quantity = get_number_or_default(request.POST.get('stock_quantity'), default=1, is_int=True)
                
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
                            variation_obj.price = get_number_or_default(request.POST.get(f'existing_variation_price_{index}'), default=Decimal('0.00'), is_int=False)
                            variation_obj.stock = get_number_or_default(request.POST.get(f'existing_variation_stock_{index}'), default=0, is_int=True)
                            variation_obj.save()
                
                existing_variation_ids_db = set(product.variations.values_list('id', flat=True))
                variations_to_delete = existing_variation_ids_db.difference(submitted_variation_ids)
                VendorProductVariation.objects.filter(id__in=variations_to_delete).delete()

                # --- CORRECTED LOGIC FOR NEW VARIATIONS ---
                new_variation_indices = set()
                for key in request.POST:
                    if key.startswith('new_variation_'):
                        index_str = key.split('_')[-1]
                        if index_str.isdigit():
                            new_variation_indices.add(int(index_str))

                for i in sorted(list(new_variation_indices)):
                    size = request.POST.get(f'new_variation_size_{i}', '')
                    color = request.POST.get(f'new_variation_color_{i}', '')
                    weight = request.POST.get(f'new_variation_weight_{i}', '')
                    price = request.POST.get(f'new_variation_price_{i}', '')
                    stock = request.POST.get(f'new_variation_stock_{i}', '')
                    
                    if size or color or weight or price or stock:
                        VendorProductVariation.objects.create(
                            product=product,
                            size=size,
                            color=color,
                            weight=weight,
                            price=get_number_or_default(price, default=Decimal('0.00'), is_int=False),
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
    user = request.user

    # Ensure the user is an approved vendor
    if user.vendor_status != 'approved':
        messages.error(request, "You do not have a vendor profile to edit.")
        return redirect('some_other_page')  # Change to a valid page name

    if request.method == 'POST':
        form = VendorProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('dashboard:vendor_profile_view')
    else:
        form = VendorProfileForm(instance=user)

    context = {
        'form': form,
    }
    return render(request, 'dashboard/vendor_profile_edit.html', context)


@login_required
def vendor_profile_view(request):
    profile = request.user
    # Check if the user is a vendor (you may have a field like is_vendor or vendor_status)
    if not getattr(profile, 'is_vendor', False) and profile.vendor_status != 'approved':
        messages.error(request, "You do not have vendor access or your vendor application is not approved.")
        return redirect('dashboard:vendor_dashboard')

    context = {
        'profile': profile,
    }
    return render(request, 'dashboard/vendor_profile_view.html', context)


@login_required
def vendor_my_orders(request):
    vendor_orders_list = VendorOrder.objects.filter(vendor=request.user).order_by('-created_at')
    vendor_products_qs = VendorProduct.objects.filter(vendor=request.user)
    vendor_products = {str(v.id): v for v in vendor_products_qs}
    status_counts = Counter(vendor_orders_list.values_list('status', flat=True))

    # Define status choices statically
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    # --- Search and Filter Logic ---
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    if search_query:
        vendor_orders_list = vendor_orders_list.filter(
            Q(id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )

    if status_filter:
        vendor_orders_list = vendor_orders_list.filter(status=status_filter)

    # --- Pagination Logic ---
    paginator = Paginator(vendor_orders_list, 10)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # --- Financial Calculation Logic ---
    for order in page_obj:
        items_list = order.items_json
        vendor_amount = Decimal('0.00')

        # Calculate item subtotal and vendor amount for each item
        for item in items_list:
            item_price = Decimal(str(item.get('price', 0)))
            item_quantity = int(item.get('quantity', 0))
            item_product_id = item.get('product_id')
            
            item['subtotal'] = item_price * item_quantity
            
            # Use a try-except block in case vendor_products is missing the item
            try:
                vendor_product = vendor_products[str(item_product_id)]
                vendor_price = Decimal(str(vendor_product.vendor_price))
                vendor_amount += vendor_price * item_quantity
            except (KeyError, TypeError):
                # Handle cases where the product ID or vendor price is not found
                # For safety, we can just skip or log this issue.
                pass
        
        # Calculate the admin amount for the order
        try:
            total_price = Decimal(str(order.total_price))
        except (ValueError, TypeError):
            total_price = Decimal('0.00')

        admin_amount = total_price - vendor_amount


        # Attach the calculated values to the order object for use in the template
        order.items_json = items_list
        order.vendor_amount = vendor_amount
        order.admin_amount = admin_amount

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(VendorOrder, id=order_id, vendor=request.user)
        
        form = VendorOrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Status for Order #{order.id} updated successfully.")
        else:
            messages.error(request, f"Failed to update status for Order #{order.id}.")
        
        return redirect('dashboard:vendor_my_orders')

    forms_dict = {order.id: VendorOrderStatusForm(instance=order) for order in page_obj}

    context = {
        'page_obj': page_obj,
        'forms_dict': forms_dict,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': STATUS_CHOICES,
        'vendor_products': vendor_products,
        'status_counts': {
            'processing': status_counts.get('processing', 0),
            'shipped': status_counts.get('shipped', 0),
            'delivered': status_counts.get('delivered', 0),
            'canceled': status_counts.get('canceled', 0),
        }
    }
    
    return render(request, 'dashboard/vendor_my_orders.html', context)



@login_required
def vendor_financial_summary_view(request):
    """
    View for displaying vendor's financial summary and transaction history
    with pagination and comprehensive financial data.
    """
    try:
        # 1. Get or create financial summary for the vendor
        vendor_summary, created = VendorFinancialSummary.objects.get_or_create(
            vendor=request.user
        )
        
        # 2. Get transactions with related order data for performance
        transactions = VendorFinancialTransaction.objects.filter(
            vendor=request.user
        ).select_related('order').order_by('-transaction_date')
        
        # 3. Set up pagination
        paginator = Paginator(transactions, 10)  # Show 10 transactions per page
        page_number = request.GET.get('page')
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # 4. Prepare context data
        context = {
            'summary': {
                'total_revenue': vendor_summary.total_revenue or 0,
                'total_vendor_amount': vendor_summary.total_vendor_amount or 0,
                'total_admin_amount': vendor_summary.total_admin_amount or 0,
                'total_orders': transactions.count(),
                'last_transaction_date': transactions.first().transaction_date if transactions.exists() else None,
            },
            'transactions': page_obj,
            'current_date': timezone.now().date(),
            'page_obj': page_obj,  # For pagination controls
        }
        
        return render(request, 'dashboard/vendor_financial_summary.html', context)
    
    except Exception as e:
        # Log the error (in production, you'd use proper logging)
        print(f"Error in vendor_financial_summary_view: {str(e)}")
        
        # Return a simplified error context
        return render(request, 'dashboard/vendor_financial_summary.html', {
            'error': 'Unable to load financial data. Please try again later.'
        })



@login_required
def vendor_download_transactions_view(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if not start_date_str or not end_date_str:
        messages.error(request, "Please provide both start and end dates.")
        return redirect('dashboard:vendor_dashboard')  # Change this to your dashboard or form page URL

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('dashboard:vendor_dashboard')

    transactions = VendorFinancialTransaction.objects.filter(
        vendor=request.user,
        transaction_date__date__range=(start_date, end_date)
    ).select_related('order').order_by('transaction_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="transactions_{start_date_str}_to_{end_date_str}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Transaction Date', 'Order Price (৳)', 'My Amount (৳)', 'Admin Amount (৳)'])

    for transaction in transactions:
        writer.writerow([
            transaction.order.id,
            transaction.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            f'{transaction.order_price:.2f}',
            f'{transaction.vendor_amount:.2f}',
            f'{transaction.admin_amount:.2f}',
        ])

    return response