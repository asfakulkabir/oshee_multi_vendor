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

    if category:
        # Products are filtered ONLY by the selected category, not its descendants.
        # If you need descendants, you'd need a custom recursive function here.
        products = Product.objects.filter(categories=category).distinct()
    else:
        products = Product.objects.all().distinct()

    available_colors = ProductVariation.objects.filter(
        product__in=products, color__isnull=False
    ).exclude(color__exact='').values_list('color', flat=True).distinct().order_by('color')

    available_sizes = ProductVariation.objects.filter(
        product__in=products, size__isnull=False
    ).exclude(size__exact='').values_list('size', flat=True).distinct().order_by('size')

    available_weights = ProductVariation.objects.filter(
        product__in=products, weight__isnull=False
    ).exclude(weight__exact='').values_list('weight', flat=True).distinct().order_by('weight')

    agg_prices = products.aggregate(min_price=Min('regular_price'), max_price=Max('regular_price'))
    min_price_overall = agg_prices['min_price'] if agg_prices['min_price'] is not None else 0
    max_price_overall = agg_prices['max_price'] if agg_prices['max_price'] is not None else 1000

    available_filters = {
        'colors': list(available_colors),
        'sizes': list(available_sizes),
        'weights': list(available_weights),
    }

    selected_min = request.GET.get('min_price')
    selected_max = request.GET.get('max_price')
    selected_colors = request.GET.getlist('color')
    selected_sizes = request.GET.getlist('size')
    selected_weights = request.GET.getlist('weight')
    search_query = request.GET.get('search', '')
    current_sort = request.GET.get('sort_by', 'default')

    if selected_min:
        try:
            min_price_val = float(selected_min)
            products = products.filter(Q(regular_price__gte=min_price_val) | Q(sale_price__gte=min_price_val, sale_price__isnull=False))
        except ValueError:
            pass
    else:
        selected_min = min_price_overall

    if selected_max:
        try:
            max_price_val = float(selected_max)
            products = products.filter(Q(regular_price__lte=max_price_val) | Q(sale_price__lte=max_price_val, sale_price__isnull=False))
        except ValueError:
            pass
    else:
        selected_max = max_price_overall

    if selected_colors:
        products = products.filter(variations__color__in=selected_colors).distinct()

    if selected_sizes:
        products = products.filter(variations__size__in=selected_sizes).distinct()

    if selected_weights:
        products = products.filter(variations__weight__in=selected_weights).distinct()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        ).distinct()

    sort_options = {
        'default': 'Default',
        'name_asc': 'Name (A-Z)',
        'name_desc': 'Name (Z-A)',
        'price_asc': 'Price (Low to High)',
        'price_desc': 'Price (High to Low)',
    }

    if current_sort == 'name_asc':
        products = products.order_by('name')
    elif current_sort == 'name_desc':
        products = products.order_by('-name')
    elif current_sort == 'price_asc':
        products = products.order_by( 'regular_price')
    elif current_sort == 'price_desc':
        products = products.order_by( '-regular_price')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    try:
        products_page = paginator.page(page_number)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)


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
    product = get_object_or_404(Product, slug=slug)

    # Fetch all variations for the product
    variations_queryset = product.variations.all()

    # Extract distinct non-empty colors, sizes, and weights for displaying buttons
    colors = variations_queryset.values_list('color', flat=True).filter(color__isnull=False).exclude(color__exact='').distinct()
    sizes = variations_queryset.values_list('size', flat=True).filter(size__isnull=False).exclude(size__exact='').distinct()
    weights = variations_queryset.values_list('weight', flat=True).filter(weight__isnull=False).exclude(weight__exact='').distinct()

    # Prepare variations data for JavaScript (JSON serialization)
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    # Get values as a list of dictionaries for JSON serialization
    # Ensure 'id', 'color', 'size', 'weight', 'price', 'stock' are present in your ProductVariation model
    variations_list = list(variations_queryset.values('id', 'color', 'size', 'weight', 'price', 'stock'))
    variations_json = json.dumps(variations_list, default=decimal_to_float)

    # Fetch related products (assuming you have a 'related_products' method or manager)
    # This is placeholder based on your template, adjust as needed.
    # For example, by category:
    related_products = Product.objects.filter(categories__in=product.categories.all()).exclude(pk=product.pk).distinct()[:5]


    context = {
        'product': product,
        'variations': variations_queryset, # Keep for templating loops
        'variations_json': variations_json,
        'colors': colors, # Passed as distinct values for buttons
        'sizes': sizes,   # Passed as distinct values for buttons
        'weights': weights, # Passed as distinct values for buttons
        'related_products': related_products,
    }
    return render(request, 'website/product_detail.html', context)



def shop(request):
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
            # Get cart items from the POST request
            cart_items_json = request.POST.get('cart_items')
            if not cart_items_json:
                return JsonResponse({'error': 'Cart items are missing'}, status=400)

            # Parse the cart items JSON
            cart_items = json.loads(cart_items_json)

            # Validate cart items
            if not isinstance(cart_items, list):
                return JsonResponse({'error': 'Invalid cart items format'}, status=400)

            # Calculate the total of all products
            total_amount = 0
            for item in cart_items:
                if not isinstance(item, dict) or 'price' not in item or 'quantity' not in item:
                    return JsonResponse({'error': 'Invalid item format in cart'}, status=400)
                total_amount += item['price'] * item['quantity']

            # Get delivery zone and charge
            delivery_zone = request.POST.get('delivery_zone')
            if not delivery_zone:
                return JsonResponse({'error': 'Delivery zone is missing'}, status=400)

            try:
                delivery_charge = DeliveryCharge.objects.get(zone=delivery_zone)
            except DeliveryCharge.DoesNotExist:
                return JsonResponse({'error': 'Invalid delivery zone'}, status=400)

            # Calculate grand total
            grand_total = total_amount + delivery_charge.charge
            # Save the order
            order = Ecommercecheckouts.objects.create(
                items_json=json.dumps(cart_items),
                customer_name=request.POST.get('customer_name', ''),
                customer_phone=request.POST.get('customer_phone_number', ''),
                customer_address=request.POST.get('customer_address', ''),
                delivery_charge=delivery_charge,
                total_amount=grand_total,
                status='processing'
            )

            # Clear the cart after successful order placement
            if 'cart' in request.session:
                del request.session['cart']

            return redirect('/order_success/?orderid='+str(order.id))  # Redirect to a success page

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Get all delivery zones for the form
    delivery_zones = DeliveryCharge.objects.all()

    return render(request, 'website/checkout_ecommerce.html', {'delivery_zones': delivery_zones})


def order_success(request):
    order_id = request.GET.get('orderid')
    if not order_id:
        # Handle case where orderid is missing, maybe redirect to home or an error page
        return redirect('/')

    order = get_object_or_404(Ecommercecheckouts, id=order_id)
    items_json_data = json.loads(order.items_json)

    return render(request, 'website/order_success.html', {
        'orderid': order.id,
        'items_json': items_json_data # Pass the parsed JSON directly
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