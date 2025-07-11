from django.urls import path
from . import views


app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<path:full_slug>/', views.category_detail, name='category_detail'),
    path('product/<str:slug>/', views.product_detail, name='product_detail'),
    path('wishlist/', views.wishlist_page_view, name='wishlist_page'),
    path('api/wishlist-products/', views.wishlist_products_api, name='wishlist_products_api'),
    path('shop/', views.shop, name='shop'),
    path('checkout_ecommerce/', views.checkout_ecommerce, name='checkout_ecommerce'),
    path('order_success/', views.order_success, name='order_success'),
    path('search/', views.search, name='search'),
    path('track-order/', views.track_order, name='track_order'),
]

