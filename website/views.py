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

def category_detail(request, full_slug=None):
    category = None
    if full_slug:
        category = get_object_or_404(Category, slug=full_slug.split('/')[-1])

    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')

    product_qs = Product.objects.filter(is_active=True)
    vendor_product_qs = VendorProduct.objects.filter(is_active=True, status='approved')

    if category:
        product_qs = product_qs.filter(categories=category).distinct()
        vendor_product_qs = vendor_product_qs.filter(categories=category).distinct()

    combined_products = list(product_qs) + list(vendor_product_qs)

    # Filter options
    selected_min = request.GET.get('min_price')
    selected_max = request.GET.get('max_price')
    selected_colors = request.GET.getlist('color')
    selected_sizes = request.GET.getlist('size')
    selected_weights = request.GET.getlist('weight')
    search_query = request.GET.get('search', '')
    current_sort = request.GET.get('sort_by', 'default')

    # Apply price filtering
    def get_price(product):
        return product.sale_price if getattr(product, 'sale_price', None) else product.regular_price

    if selected_min:
        try:
            min_price_val = float(selected_min)
            combined_products = [p for p in combined_products if get_price(p) >= min_price_val]
        except ValueError:
            pass

    if selected_max:
        try:
            max_price_val = float(selected_max)
            combined_products = [p for p in combined_products if get_price(p) <= max_price_val]
        except ValueError:
            pass

    # Filter by color/size/weight (only applicable for ProductVariation)
    if selected_colors or selected_sizes or selected_weights:
        filtered_ids = ProductVariation.objects.filter(
            Q(product__in=[p.id for p in combined_products if isinstance(p, Product)]) |
            Q(product__in=[p.id for p in combined_products if isinstance(p, VendorProduct)])
        )

        if selected_colors:
            filtered_ids = filtered_ids.filter(color__in=selected_colors)
        if selected_sizes:
            filtered_ids = filtered_ids.filter(size__in=selected_sizes)
        if selected_weights:
            filtered_ids = filtered_ids.filter(weight__in=selected_weights)

        valid_product_ids = filtered_ids.values_list('product_id', flat=True).distinct()
        combined_products = [p for p in combined_products if p.id in valid_product_ids]

    # Search query
    if search_query:
        combined_products = [
            p for p in combined_products if search_query.lower() in p.name.lower()
        ]

    # Sort options
    sort_options = {
        'default': 'Default',
        'name_asc': 'Name (A-Z)',
        'name_desc': 'Name (Z-A)',
        'price_asc': 'Price (Low to High)',
        'price_desc': 'Price (High to Low)',
    }

    if current_sort == 'name_asc':
        combined_products.sort(key=lambda p: p.name.lower())
    elif current_sort == 'name_desc':
        combined_products.sort(key=lambda p: p.name.lower(), reverse=True)
    elif current_sort == 'price_asc':
        combined_products.sort(key=lambda p: get_price(p))
    elif current_sort == 'price_desc':
        combined_products.sort(key=lambda p: get_price(p), reverse=True)
    else:
        combined_products.sort(key=lambda p: p.created_at, reverse=True)

    # Price range (for filter UI)
    all_prices = [get_price(p) for p in combined_products]
    min_price_overall = min(all_prices) if all_prices else 0
    max_price_overall = max(all_prices) if all_prices else 1000

    # Available filters
    available_colors = ProductVariation.objects.filter(
        color__isnull=False
    ).exclude(color__exact='').values_list('color', flat=True).distinct().order_by('color')

    available_sizes = ProductVariation.objects.filter(
        size__isnull=False
    ).exclude(size__exact='').values_list('size', flat=True).distinct().order_by('size')

    available_weights = ProductVariation.objects.filter(
        weight__isnull=False
    ).exclude(weight__exact='').values_list('weight', flat=True).distinct().order_by('weight')

    available_filters = {
        'colors': list(available_colors),
        'sizes': list(available_sizes),
        'weights': list(available_weights),
    }

    # Pagination
    paginator = Paginator(combined_products, 50)
    page_number = request.GET.get('page')
    try:
        products_page = paginator.page(page_number)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Wishlist (from cookies)
    wishlist_ids_cookie_str = request.COOKIES.get('wishlist_ids', '[]')
    try:
        initial_wishlist_ids = json.loads(wishlist_ids_cookie_str)
        initial_wishlist_ids = [str(id) for id in initial_wishlist_ids]
    except json.JSONDecodeError:
        initial_wishlist_ids = []

    context = {
        'category': category,
        'current_category': category.slug if category else None,
        'categories': categories,
        'products': products_page,
        'selected_min': float(selected_min) if selected_min else min_price_overall,
        'selected_max': float(selected_max) if selected_max else max_price_overall,
        'min_price': min_price_overall,
        'max_price': max_price_overall,
        'available_filters': available_filters,
        'selected_colors': selected_colors,
        'selected_sizes': selected_sizes,
        'selected_weights': selected_weights,
        'search_query': search_query,
        'sort_options': sort_options,
        'current_sort': current_sort,
        'wishlist_ids': initial_wishlist_ids,
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
    # Filters from request
    category_slug = request.GET.get('category')
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')
    search_query = request.GET.get('search')
    color_filter = request.GET.getlist('color')
    size_filter = request.GET.getlist('size')
    weight_filter = request.GET.getlist('weight')
    sort_by = request.GET.get('sort_by', '-created_at')

    # Parse prices
    try:
        selected_min_from_url = float(min_price_param) if min_price_param else None
    except ValueError:
        selected_min_from_url = None

    try:
        selected_max_from_url = float(max_price_param) if max_price_param else None
    except ValueError:
        selected_max_from_url = None

    # Fetch all active products
    all_products = Product.objects.filter(is_active=True)
    all_vendor_products = VendorProduct.objects.filter(status='approved')

    # Aggregate prices for slider range
    all_prices = list(all_products.values_list('regular_price', flat=True)) + \
                 list(all_vendor_products.values_list('regular_price', flat=True))
    overall_min_price = min(all_prices) if all_prices else 0
    overall_max_price = max(all_prices) + 100 if all_prices else 1000

    min_price_filter = selected_min_from_url or overall_min_price
    max_price_filter = selected_max_from_url or overall_max_price
    if max_price_filter < min_price_filter:
        max_price_filter = min_price_filter

    # Initial querysets with prefetching
    products = all_products.prefetch_related('images', 'variations')
    vendor_products = all_vendor_products.prefetch_related('images', 'variations')

    # Category filter
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

    # Price filter
    price_filter = Q(regular_price__gte=min_price_filter, regular_price__lte=max_price_filter) | \
                   Q(sale_price__gte=min_price_filter, sale_price__lte=max_price_filter, sale_price__isnull=False)
    products = products.filter(price_filter)
    vendor_products = vendor_products.filter(price_filter)

    # Search filter
    if search_query:
        search_q = Q(name__icontains=search_query) | Q(short_description__icontains=search_query) | Q(description__icontains=search_query) | Q(categories__name__icontains=search_query)
        products = products.filter(search_q)
        vendor_products = vendor_products.filter(search_q)

    # Variation filters
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

    # Sorting
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

    # Combine and paginate
    combined_products = sorted(
        chain(products, vendor_products),
        key=lambda x: getattr(x, sort_by.lstrip('-')),
        reverse=sort_by.startswith('-')
    )
    paginator = Paginator(combined_products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Filters (for sidebar)
    available_filters = {
        'colors': ProductVariation.objects.filter(product__in=all_products).exclude(color='').values_list('color', flat=True).distinct(),
        'sizes': ProductVariation.objects.filter(product__in=all_products).exclude(size='').values_list('size', flat=True).distinct(),
        'weights': ProductVariation.objects.filter(product__in=all_products).exclude(weight='').values_list('weight', flat=True).distinct(),
    }

    # Wishlist
    try:
        wishlist_ids = json.loads(request.COOKIES.get('wishlist_ids', '[]'))
    except json.JSONDecodeError:
        wishlist_ids = []

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

        valid_product_ids = [pid for pid in product_ids_from_frontend if isinstance(pid, (str, int))]

        wishlist_products = Product.objects.filter(pk__in=valid_product_ids, is_active=True).order_by('name')

        serialized_products = []
        for product in wishlist_products:
            image_url = '/static/icons/default-image.webp'
            if product.images.exists() and product.images.first().image:
                image_url = product.images.first().image.url

            serialized_products.append({
                'id': str(product.id),
                'name': product.name,
                'slug': product.slug,
                'regular_price': float(product.regular_price),
                'sale_price': float(product.sale_price) if product.sale_price is not None else None,
                'image': image_url,
            })
        return JsonResponse(serialized_products, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body."}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error in wishlist_products_api:")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)




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
                    if not vendor_id:
                        return JsonResponse({'error': f"Missing vendor_id for item: {item.get('name', 'Unknown')}"}, status=400)

                    cleaned_cart_items.append({
                        'name': item.get('name', ''),
                        'image': item.get('image', ''),
                        'price': float(price),
                        'quantity': int(quantity),
                        'variation': item.get('variation', {}),
                        'vendor_id': str(vendor_id),
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
    products = Product.objects.filter(is_active=True).prefetch_related('images', 'variations')

    category_slug = request.GET.get('category')
    min_price_param = request.GET.get('min_price')
    max_price_param = request.GET.get('max_price')
    search_query = request.GET.get('search')
    color_filter = request.GET.getlist('color')
    size_filter = request.GET.getlist('size')
    weight_filter = request.GET.getlist('weight')
    sort_by = request.GET.get('sort_by', '-created_at')

    all_active_products = Product.objects.filter(is_active=True)

    overall_price_aggregates = all_active_products.aggregate(
        min_p=Min('regular_price'),
        max_p=Max('regular_price')
    )

    overall_min_price = overall_price_aggregates['min_p'] if overall_price_aggregates['min_p'] is not None else 0
    overall_max_price = overall_price_aggregates['max_p'] if overall_price_aggregates['max_p'] is not None else 1000
    overall_max_price += 100

    selected_min_from_url = None
    selected_max_from_url = None

    try:
        if min_price_param:
            selected_min_from_url = float(min_price_param)
    except ValueError:
        pass

    try:
        if max_price_param:
            selected_max_from_url = float(max_price_param)
    except ValueError:
        pass

    min_price_filter = selected_min_from_url if selected_min_from_url is not None else overall_min_price
    max_price_filter = selected_max_from_url if selected_max_from_url is not None else overall_max_price

    if max_price_filter < min_price_filter:
        max_price_filter = min_price_filter

    if category_slug:
        if '/' in category_slug:
            last_slug = category_slug.split('/')[-1]
            category = Category.objects.filter(slug=last_slug).first()
        else:
            category = Category.objects.filter(slug=category_slug).first()

        if category:
            def get_descendants(cat):
                descendants = list(cat.children.all())
                for child in cat.children.all():
                    descendants.extend(get_descendants(child))
                return descendants

            all_categories = [category] + get_descendants(category)
            products = products.filter(categories__in=all_categories).distinct()

    if min_price_filter is not None or max_price_filter is not None:
        if min_price_filter is not None and max_price_filter is not None:
            products = products.filter(
                Q(regular_price__gte=min_price_filter, regular_price__lte=max_price_filter) |
                Q(sale_price__gte=min_price_filter, sale_price__lte=max_price_filter, sale_price__isnull=False)
            ).distinct()
        elif min_price_filter is not None:
            products = products.filter(
                Q(regular_price__gte=min_price_filter) |
                Q(sale_price__gte=min_price_filter, sale_price__isnull=False)
            ).distinct()
        elif max_price_filter is not None:
            products = products.filter(
                Q(regular_price__lte=max_price_filter) |
                Q(sale_price__lte=max_price_filter, sale_price__isnull=False)
            ).distinct()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(categories__name__icontains=search_query)
        ).distinct()

    variation_filters = Q()
    if color_filter:
        variation_filters &= Q(variations__color__in=color_filter)
    if size_filter:
        variation_filters &= Q(variations__size__in=size_filter)
    if weight_filter:
        variation_filters &= Q(variations__weight__in=weight_filter)

    if variation_filters:
        products = products.filter(variation_filters).distinct()

    valid_sort_options = {
        '-created_at': 'Newest',
        'created_at': 'Oldest',
        'name': 'Name (A-Z)',
        '-name': 'Name (Z-A)',
        'regular_price': 'Price (Low to High)',
        '-regular_price': 'Price (High to Low)',
    }

    if sort_by in valid_sort_options:
        products = products.order_by(sort_by)
    else:
        sort_by = '-created_at'
        products = products.order_by(sort_by)

    available_filters = {
        'colors': ProductVariation.objects.filter(product__in=all_active_products)
                                .exclude(color__isnull=True).exclude(color__exact='')
                                .values_list('color', flat=True).distinct().order_by('color'),
        'sizes': ProductVariation.objects.filter(product__in=all_active_products)
                                .exclude(size__isnull=True).exclude(size__exact='')
                                .values_list('size', flat=True).distinct().order_by('size'),
        'weights': ProductVariation.objects.filter(product__in=all_active_products)
                                .exclude(weight__isnull=True).exclude(weight__exact='')
                                .values_list('weight', flat=True).distinct().order_by('weight'),
    }

    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    wishlist_ids_cookie_str = request.COOKIES.get('wishlist_ids', '[]')
    try:
        initial_wishlist_ids = json.loads(wishlist_ids_cookie_str)
        initial_wishlist_ids = [str(id) for id in initial_wishlist_ids]
    except json.JSONDecodeError:
        initial_wishlist_ids = []


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