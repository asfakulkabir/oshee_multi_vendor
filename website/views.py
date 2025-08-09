from products.models import *
from .models import *
from django.shortcuts import render, get_object_or_404, redirect
import json
from decimal import Decimal
from django.views import View
from django.db.models import Q, Min, Max
from django.http import Http404
from .forms import ProductFilterForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import math
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from orders.models import *
from itertools import chain


def home(request):
    testimonials_desktop = Testimonial.objects.filter(is_active=True, for_mobile=False)
    testimonials_mobile = Testimonial.objects.filter(is_active=True, for_mobile=True)
    desktop_banners = Banner.objects.filter(is_active=True, for_mobile=False).order_by('-created_at')
    mobile_banners = Banner.objects.filter(is_active=True, for_mobile=True).order_by('-created_at')
    categories = Category.objects.all()[:13]
    popular_products = Product.objects.filter(is_featured=True)[:8]
    home_components = HomeComponents.objects.all()
    return render(request, 'website/home.html', {
        'categories': categories,
        'popular_products': popular_products,
        'desktop_banners': desktop_banners,
        'mobile_banners': mobile_banners,
        'testimonials_desktop': testimonials_desktop,
        'testimonials_mobile': testimonials_mobile,
        'home_components':home_components,
    })

# Helper function to get all descendant categories
def get_descendants(category):
    """Recursively gets a category and all its children/grandchildren."""
    descendants = []
    children = category.children.all()
    for child in children:
        descendants.append(child)
        descendants.extend(get_descendants(child))
    return descendants

def category_detail(request, full_slug=None):
    # --- Filters from request ---
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')
    search_query = request.GET.get('search', '').strip()
    color_filter = request.GET.getlist('color')
    size_filter = request.GET.getlist('size')
    weight_filter = request.GET.getlist('weight')
    sort_by = request.GET.get('sort_by', '-created_at')

    # --- Fetch category and top-level categories ---
    current_category = None
    if full_slug:
        slug = full_slug.split('/')[-1]
        current_category = get_object_or_404(Category, slug=slug)

    categories_for_menu = Category.objects.filter(parent__isnull=True).prefetch_related('children')

    # --- Initial QuerySets ---
    products_qs = Product.objects.filter(is_active=True)
    vendor_products_qs = VendorProduct.objects.filter(is_active=True, status='approved')

    # --- Category filter (applies to querysets) ---
    if current_category:
        descendant_categories = [current_category] + get_descendants(current_category)
        products_qs = products_qs.filter(categories__in=descendant_categories).distinct()
        vendor_products_qs = vendor_products_qs.filter(categories__in=descendant_categories).distinct()
    
    # --- Pre-calculate filter ranges based on the filtered querysets ---
    all_prices_in_qs = list(products_qs.values_list('regular_price', flat=True)) + \
                       list(vendor_products_qs.values_list('regular_price', flat=True))
    all_sale_prices_in_qs = list(products_qs.exclude(sale_price__isnull=True).values_list('sale_price', flat=True)) + \
                            list(vendor_products_qs.exclude(sale_price__isnull=True).values_list('sale_price', flat=True))
    
    all_prices_for_range = [p for p in all_prices_in_qs + all_sale_prices_in_qs if p is not None]
    
    overall_min_price = min(all_prices_for_range) if all_prices_for_range else 0
    overall_max_price = max(all_prices_for_range) if all_prices_for_range else 1000

    # --- Parse and apply price filters to querysets ---
    try:
        selected_min = float(min_price_param) if min_price_param else overall_min_price
    except (ValueError, TypeError):
        selected_min = overall_min_price
    
    try:
        selected_max = float(max_price_param) if max_price_param else overall_max_price
    except (ValueError, TypeError):
        selected_max = overall_max_price

    if selected_max < selected_min:
        selected_max = selected_min

    price_q = Q(Q(regular_price__gte=selected_min, regular_price__lte=selected_max) |
                Q(sale_price__gte=selected_min, sale_price__lte=selected_max, sale_price__isnull=False))
    
    products_qs = products_qs.filter(price_q)
    vendor_products_qs = vendor_products_qs.filter(price_q)

    # --- Search filter (applies to querysets) ---
    if search_query:
        search_q = Q(name__icontains=search_query) | Q(short_description__icontains=search_query) | \
                   Q(description__icontains=search_query) | Q(categories__name__icontains=search_query)
        products_qs = products_qs.filter(search_q)
        vendor_products_qs = vendor_products_qs.filter(search_q)

    # --- Variation filters (applies to querysets) ---
    variation_q = Q()
    if color_filter:
        variation_q &= Q(variations__color__in=color_filter)
    if size_filter:
        variation_q &= Q(variations__size__in=size_filter)
    if weight_filter:
        variation_q &= Q(variations__weight__in=weight_filter)
    
    if variation_q:
        products_qs = products_qs.filter(variation_q).distinct()
        vendor_products_qs = vendor_products_qs.filter(variation_q).distinct()

    # --- Sorting (applies to querysets) ---
    valid_sort_options = {
        '-created_at': 'Newest',
        'created_at': 'Oldest',
        'name': 'Name (A-Z)',
        '-name': 'Name (Z-A)',
        'regular_price': 'Price (Low to High)',
        '-regular_price': 'Price (High to Low)',
    }
    sort_by = sort_by if sort_by in valid_sort_options else '-created_at'
    products_qs = products_qs.order_by(sort_by)
    vendor_products_qs = vendor_products_qs.order_by(sort_by)

    # --- Combine QuerySets + Paginate ---
    combined_products = list(products_qs) + list(vendor_products_qs)

    paginator = Paginator(combined_products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- Sidebar filters (dynamic, based on the filtered querysets) ---
    filtered_product_ids = list(products_qs.values_list('id', flat=True))
    filtered_vendor_product_ids = list(vendor_products_qs.values_list('id', flat=True))

    product_variations_qs = ProductVariation.objects.filter(product_id__in=filtered_product_ids)
    vendor_product_variations_qs = VendorProductVariation.objects.filter(product_id__in=filtered_vendor_product_ids)

    # Get available colors
    all_colors = (
        set(product_variations_qs.exclude(color__exact='').values_list('color', flat=True).distinct())
        .union(set(vendor_product_variations_qs.exclude(color__exact='').values_list('color', flat=True).distinct()))
    )
    colors = sorted([c for c in all_colors if c is not None])

    # Get available sizes
    all_sizes = (
        set(product_variations_qs.exclude(size__exact='').values_list('size', flat=True).distinct())
        .union(set(vendor_product_variations_qs.exclude(size__exact='').values_list('size', flat=True).distinct()))
    )
    sizes = sorted([s for s in all_sizes if s is not None])

    # Get available weights
    all_weights = (
        set(product_variations_qs.exclude(weight__exact='').values_list('weight', flat=True).distinct())
        .union(set(vendor_product_variations_qs.exclude(weight__exact='').values_list('weight', flat=True).distinct()))
    )
    weights = sorted([w for w in all_weights if w is not None])

    available_filters = {
        'colors': colors,
        'sizes': sizes,
        'weights': weights,
    }

    # --- Wishlist from cookies ---
    try:
        wishlist_ids = json.loads(request.COOKIES.get('wishlist_ids', '[]'))
        wishlist_ids = [str(w) for w in wishlist_ids]
    except json.JSONDecodeError:
        wishlist_ids = []

    # --- Context for template ---
    context = {
        'products': page_obj,
        'categories': categories_for_menu,
        'min_price': overall_min_price,
        'max_price': overall_max_price,
        'selected_min': selected_min,
        'selected_max': selected_max,
        'available_filters': available_filters,
        'selected_colors': color_filter,
        'selected_sizes': size_filter,
        'selected_weights': weight_filter,
        'sort_options': valid_sort_options,
        'current_sort': sort_by,
        'search_query': search_query,
        'current_category': current_category,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'website/category_detail.html', context)
def product_detail(request, slug):
    try:
        product = Product.objects.get(slug=slug)
        is_vendor_product = False
    except Product.DoesNotExist:
        product = get_object_or_404(VendorProduct, slug=slug, is_active=True, status='approved')
        is_vendor_product = True

    # Fetch all variations
    variations_queryset = product.variations.all()

    # Extract distinct attributes
    colors = variations_queryset.filter(color__isnull=False).exclude(color__exact='').values_list('color', flat=True).distinct()
    sizes = variations_queryset.filter(size__isnull=False).exclude(size__exact='').values_list('size', flat=True).distinct()
    weights = variations_queryset.filter(weight__isnull=False).exclude(weight__exact='').values_list('weight', flat=True).distinct()

    # JSON-serialize variations
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    variations_list = list(variations_queryset.values('id', 'color', 'size', 'weight', 'price', 'stock'))
    variations_json = json.dumps(variations_list, default=decimal_to_float)

    # Related products (only from Product model)
    related_products = Product.objects.filter(
        categories__in=product.categories.all()
    ).exclude(pk=product.pk).distinct()[:5]

    context = {
        'product': product,
        'is_vendor_product': is_vendor_product,
        'variations': variations_queryset,
        'variations_json': variations_json,
        'colors': colors,
        'sizes': sizes,
        'weights': weights,
        'related_products': related_products,
    }

    return render(request, 'website/product_detail.html', context)

def shop(request):
    # --- Filters from request ---
    category_slug = request.GET.get('category')
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')
    search_query = request.GET.get('search')
    color_filter = request.GET.getlist('color')
    size_filter = request.GET.getlist('size')
    weight_filter = request.GET.getlist('weight')
    sort_by = request.GET.get('sort_by', '-created_at')

    # --- Parse prices ---
    try:
        selected_min_from_url = float(min_price_param) if min_price_param else None
    except ValueError:
        selected_min_from_url = None
    try:
        selected_max_from_url = float(max_price_param) if max_price_param else None
    except ValueError:
        selected_max_from_url = None

    # --- Fetch all active products ---
    all_products = Product.objects.filter(is_active=True)
    all_vendor_products = VendorProduct.objects.filter(status='approved')

    # --- Aggregate prices ---
    all_prices = list(all_products.values_list('regular_price', flat=True)) + \
                 list(all_vendor_products.values_list('regular_price', flat=True))
    overall_min_price = min(all_prices) if all_prices else 0
    overall_max_price = max(all_prices) + 100 if all_prices else 1000

    min_price_filter = selected_min_from_url or overall_min_price
    max_price_filter = selected_max_from_url or overall_max_price
    if max_price_filter < min_price_filter:
        max_price_filter = min_price_filter

    # --- Prefetch ---
    products = all_products.prefetch_related('images', 'variations')
    vendor_products = all_vendor_products.prefetch_related('images', 'variations')

    # --- Category filter ---
    if category_slug:
        category = Category.objects.filter(slug=category_slug.split('/')[-1]).first()
        if category:
            def get_descendants(cat):
                children = list(cat.children.all())
                for child in cat.children.all():
                    children.extend(get_descendants(child))
                return children

            all_categories = [category] + get_descendants(category)
            products = products.filter(categories__in=all_categories)
            vendor_products = vendor_products.filter(categories__in=all_categories)

    # --- Price filter ---
    price_filter = Q(regular_price__gte=min_price_filter, regular_price__lte=max_price_filter) | \
                   Q(sale_price__gte=min_price_filter, sale_price__lte=max_price_filter, sale_price__isnull=False)
    products = products.filter(price_filter)
    vendor_products = vendor_products.filter(price_filter)

    # --- Search filter ---
    if search_query:
        search_q = Q(name__icontains=search_query) | Q(short_description__icontains=search_query) | \
                   Q(description__icontains=search_query) | Q(categories__name__icontains=search_query)
        products = products.filter(search_q)
        vendor_products = vendor_products.filter(search_q)

    # --- Variation filters ---
    variation_q = Q()
    if color_filter:
        variation_q &= Q(variations__color__in=color_filter)
    if size_filter:
        variation_q &= Q(variations__size__in=size_filter)
    if weight_filter:
        variation_q &= Q(variations__weight__in=weight_filter)
    if variation_q:
        products = products.filter(variation_q)
        vendor_products = vendor_products.filter(variation_q)

    # --- Sorting ---
    valid_sort_options = {
        '-created_at': 'Newest',
        'created_at': 'Oldest',
        'name': 'Name (A-Z)',
        '-name': 'Name (Z-A)',
        'regular_price': 'Price (Low to High)',
        '-regular_price': 'Price (High to Low)',
    }
    sort_by = sort_by if sort_by in valid_sort_options else '-created_at'
    products = products.order_by(sort_by)
    vendor_products = vendor_products.order_by(sort_by)

    # --- Combine + paginate ---
    combined_products = sorted(
        chain(products, vendor_products),
        key=lambda x: getattr(x, sort_by.lstrip('-')) or 0,
        reverse=sort_by.startswith('-')
    )
    paginator = Paginator(combined_products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- Sidebar filters (merged Product + VendorProduct variations) ---
    # Colors
    product_colors = ProductVariation.objects.filter(product__in=all_products).exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True).distinct()
    vendor_colors = VendorProductVariation.objects.filter(product__in=all_vendor_products).exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True).distinct()
    colors = sorted(set(product_colors).union(set(vendor_colors)))

    # Sizes
    product_sizes = ProductVariation.objects.filter(product__in=all_products).exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True).distinct()
    vendor_sizes = VendorProductVariation.objects.filter(product__in=all_vendor_products).exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True).distinct()
    sizes = sorted(set(product_sizes).union(set(vendor_sizes)))

    # Weights
    product_weights = ProductVariation.objects.filter(product__in=all_products).exclude(weight__isnull=True).exclude(weight__exact='').values_list('weight', flat=True).distinct()
    vendor_weights = VendorProductVariation.objects.filter(product__in=all_vendor_products).exclude(weight__isnull=True).exclude(weight__exact='').values_list('weight', flat=True).distinct()
    weights = sorted(set(product_weights).union(set(vendor_weights)))

    available_filters = {
        'colors': colors,
        'sizes': sizes,
        'weights': weights,
    }

    # --- Wishlist ---
    try:
        wishlist_ids = json.loads(request.COOKIES.get('wishlist_ids', '[]'))
    except json.JSONDecodeError:
        wishlist_ids = []

    # --- Context ---
    context = {
        'products': page_obj,
        'categories': Category.objects.filter(parent__isnull=True),
        'min_price': overall_min_price,
        'max_price': overall_max_price,
        'selected_min': min_price_filter,
        'selected_max': max_price_filter,
        'available_filters': available_filters,
        'selected_colors': color_filter,
        'selected_sizes': size_filter,
        'selected_weights': weight_filter,
        'sort_options': valid_sort_options,
        'current_sort': sort_by,
        'search_query': search_query or '',
        'current_category': category_slug or '',
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'website/shop.html', context)


def wishlist_page_view(request):
    return render(request, 'website/wishlist.html', {})

@require_POST
@csrf_exempt
def wishlist_products_api(request):
    if request.content_type != 'application/json':
        return JsonResponse({"error": "Content-Type must be application/json"}, status=415)

    try:
        data = json.loads(request.body)
        product_ids_from_frontend = data.get('product_ids', [])

        if not isinstance(product_ids_from_frontend, list):
            return JsonResponse({"error": "product_ids must be a list."}, status=400)

        # Separate IDs
        regular_ids = []
        vendor_ids = []

        for pid in product_ids_from_frontend:
            if isinstance(pid, str):
                if pid.startswith('p-'):
                    try:
                        regular_ids.append(int(pid.split('-')[1]))
                    except (ValueError, IndexError):
                        continue
                elif pid.startswith('v-'):
                    try:
                        vendor_ids.append(int(pid.split('-')[1]))
                    except (ValueError, IndexError):
                        continue

        regular_products = Product.objects.filter(pk__in=regular_ids, is_active=True)
        vendor_products = VendorProduct.objects.filter(pk__in=vendor_ids, status='approved')

        all_wishlist_products = list(regular_products) + list(vendor_products)
        all_wishlist_products.sort(key=lambda x: x.name or "")

        serialized_products = []
        for product in all_wishlist_products:
            image_url = '/static/icons/default-image.webp'
            product_images = getattr(product, 'images', None)

            if product_images and product_images.exists() and product_images.first().image:
                image_url = product_images.first().image.url

            sale_price = float(product.sale_price) if product.sale_price else None
            regular_price = float(product.regular_price) if product.regular_price else 0.0

            serialized_products.append({
                'id': product.prefixed_id,
                'name': product.name,
                'slug': product.slug,
                'regular_price': regular_price,
                'sale_price': sale_price,
                'image': image_url,
            })

        return JsonResponse(serialized_products, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body."}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error in wishlist_products_api:")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)
    
    
def checkout_ecommerce(request):
    if request.method == 'POST':
        try:
            cart_items_json = request.POST.get('cart_items')
            if not cart_items_json:
                return JsonResponse({'error': 'Cart items are missing'}, status=400)

            cart_items = json.loads(cart_items_json)
            if not isinstance(cart_items, list):
                cart_items = [cart_items]

            total_amount = Decimal('0.0')
            cleaned_cart_items = []

            for item in cart_items:
                try:
                    price = Decimal(str(item['price']))
                    quantity = Decimal(str(item['quantity']))
                    total_amount += price * quantity

                    vendor_id = item.get('vendor_id')
                    if vendor_id in [None, '']:
                        return JsonResponse({'error': f"Missing vendor_id for item: {item.get('name', 'Unknown')}"}, status=400)

                    cleaned_cart_items.append({
                        'name': item.get('name', ''),
                        'image': item.get('image', ''),
                        'price': float(price),
                        'quantity': int(quantity),
                        'variation': item.get('variation', {}),
                        'vendor_id': str(vendor_id),
                        'product_id': str(item.get('product_id')),
                    })
                except Exception as item_error:
                    return JsonResponse({'error': f"Error processing item: {item_error}"}, status=400)

            delivery_zone = request.POST.get('delivery_zone')
            if not delivery_zone:
                return JsonResponse({'error': 'Delivery zone is missing'}, status=400)

            try:
                delivery_charge = DeliveryCharge.objects.get(zone=delivery_zone)
            except DeliveryCharge.DoesNotExist:
                return JsonResponse({'error': 'Invalid delivery zone'}, status=400)

            grand_total = total_amount + delivery_charge.charge

            order = Ecommercecheckouts.objects.create(
                items_json=cleaned_cart_items,
                customer_name=request.POST.get('customer_name', ''),
                customer_phone=request.POST.get('customer_phone_number', ''),
                customer_address=request.POST.get('customer_address', ''),
                delivery_charge=delivery_charge,
                total_amount=grand_total,
                status='processing'
            )

            return redirect('/order_success/?orderid=' + str(order.id))

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    delivery_zones = DeliveryCharge.objects.all()
    return render(request, 'website/checkout_ecommerce.html', {'delivery_zones': delivery_zones})

def order_success(request):
    order_id = request.GET.get('orderid')
    if not order_id:
        return redirect('/')  # Redirect if order ID missing

    order = get_object_or_404(Ecommercecheckouts, id=order_id)

    return render(request, 'website/order_success.html', {
        'orderid': order.id,
        'items_json': order.items_json,  # Already a Python list/dict
        'order': order,
    })

def search(request):
    category_slug = request.GET.get('category')
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')
    search_query = request.GET.get('search')
    color_filter = request.GET.getlist('color')
    size_filter = request.GET.getlist('size')
    weight_filter = request.GET.getlist('weight')
    sort_by = request.GET.get('sort_by', '-created_at')

    # Base queries
    products_qs = Product.objects.filter(is_active=True)
    vendor_products_qs = VendorProduct.objects.filter(status='approved', is_active=True)

    # Price range calculation
    overall_min_price = min(
        products_qs.aggregate(p=Min('regular_price'))['p'] or float('inf'),
        vendor_products_qs.aggregate(p=Min('regular_price'))['p'] or float('inf')
    )
    overall_max_price = max(
        products_qs.aggregate(p=Max('regular_price'))['p'] or 0,
        vendor_products_qs.aggregate(p=Max('regular_price'))['p'] or 0
    )
    if overall_min_price == float('inf'):
        overall_min_price = 0
    overall_max_price += 100

    # Selected price from request
    try:
        selected_min = float(min_price_param) if min_price_param else overall_min_price
    except ValueError:
        selected_min = overall_min_price

    try:
        selected_max = float(max_price_param) if max_price_param else overall_max_price
    except ValueError:
        selected_max = overall_max_price

    if selected_max < selected_min:
        selected_max = selected_min

    # Category filtering
    if category_slug:
        last_slug = category_slug.split('/')[-1]
        category = Category.objects.filter(slug=last_slug).first()
        if category:
            def get_descendants(cat):
                descendants = list(cat.children.all())
                for child in cat.children.all():
                    descendants.extend(get_descendants(child))
                return descendants
            all_categories = [category] + get_descendants(category)
            products_qs = products_qs.filter(categories__in=all_categories).distinct()
            vendor_products_qs = vendor_products_qs.filter(categories__in=all_categories).distinct()

    # Price filtering
    price_filter = Q(regular_price__gte=selected_min, regular_price__lte=selected_max) | \
                   Q(sale_price__gte=selected_min, sale_price__lte=selected_max, sale_price__isnull=False)
    products_qs = products_qs.filter(price_filter).distinct()
    vendor_products_qs = vendor_products_qs.filter(price_filter).distinct()

    # Search filtering
    if search_query:
        search_q = Q(name__icontains=search_query) | \
                   Q(short_description__icontains=search_query) | \
                   Q(description__icontains=search_query) | \
                   Q(categories__name__icontains=search_query)
        products_qs = products_qs.filter(search_q).distinct()
        vendor_products_qs = vendor_products_qs.filter(search_q).distinct()

    # Variation filters
    variation_q = Q()
    if color_filter:
        variation_q &= Q(variations__color__in=color_filter)
    if size_filter:
        variation_q &= Q(variations__size__in=size_filter)
    if weight_filter:
        variation_q &= Q(variations__weight__in=weight_filter)
    if variation_q:
        products_qs = products_qs.filter(variation_q).distinct()

    vendor_variation_q = Q()
    if color_filter:
        vendor_variation_q &= Q(vendor_variations__color__in=color_filter)
    if size_filter:
        vendor_variation_q &= Q(vendor_variations__size__in=size_filter)
    if weight_filter:
        vendor_variation_q &= Q(vendor_variations__weight__in=weight_filter)
    if vendor_variation_q:
        vendor_products_qs = vendor_products_qs.filter(vendor_variation_q).distinct()

    # Combine all products
    all_combined = list(products_qs) + list(vendor_products_qs)

    # Sorting
    valid_sort_options = {
        '-created_at': 'Newest',
        'created_at': 'Oldest',
        'name': 'Name (A-Z)',
        '-name': 'Name (Z-A)',
        'regular_price': 'Price (Low to High)',
        '-regular_price': 'Price (High to Low)',
    }
    if sort_by in valid_sort_options:
        reverse = sort_by.startswith('-')
        key = sort_by.lstrip('-')
        all_combined.sort(key=lambda x: getattr(x, key, 0) or 0, reverse=reverse)
    else:
        sort_by = '-created_at'
        all_combined.sort(key=lambda x: getattr(x, 'created_at', None) or 0, reverse=True)

    # Pagination
    paginator = Paginator(all_combined, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Filters (without None/empty values)
    variation_qs = ProductVariation.objects.filter(product__in=products_qs)
    vendor_variation_qs = VendorProductVariation.objects.filter(product__in=vendor_products_qs)

    colors = sorted(set(
        list(variation_qs.exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True)) +
        list(vendor_variation_qs.exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True))
    ))

    sizes = sorted(set(
        list(variation_qs.exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True)) +
        list(vendor_variation_qs.exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True))
    ))

    weights = sorted(set(
        list(variation_qs.exclude(weight__isnull=True).exclude(weight__exact='').values_list('weight', flat=True)) +
        list(vendor_variation_qs.exclude(weight__isnull=True).exclude(weight__exact='').values_list('weight', flat=True))
    ))

    # Wishlist
    wishlist_ids_cookie_str = request.COOKIES.get('wishlist_ids', '[]')
    try:
        initial_wishlist_ids = [str(i) for i in json.loads(wishlist_ids_cookie_str)]
    except json.JSONDecodeError:
        initial_wishlist_ids = []

    context = {
        'products': page_obj,
        'categories': Category.objects.filter(parent__isnull=True),
        'min_price': overall_min_price,
        'max_price': overall_max_price,
        'selected_min': selected_min,
        'selected_max': selected_max,
        'available_filters': {
            'colors': colors,
            'sizes': sizes,
            'weights': weights,
        },
        'selected_colors': color_filter,
        'selected_sizes': size_filter,
        'selected_weights': weight_filter,
        'sort_options': valid_sort_options,
        'current_sort': sort_by,
        'search_query': search_query or '',
        'current_category': category_slug or '',
        'wishlist_ids': initial_wishlist_ids,
    }
    return render(request, 'website/search.html', context)

def track_order(request):
    orders = None
    phone_number = None
    error_message = None

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')

        if phone_number:
            cleaned_phone_number = phone_number.strip().replace(" ", "")

            orders = Ecommercecheckouts.objects.filter(customer_phone=cleaned_phone_number).order_by('-created_at')

            if not orders.exists():
                error_message = f"No orders found for mobile number: {phone_number}"
        else:
            error_message = "Please enter a mobile number."

    context = {
        'orders': orders,
        'phone_number': phone_number,
        'error_message': error_message,
    }

    return render(request, 'website/track_order.html', context)