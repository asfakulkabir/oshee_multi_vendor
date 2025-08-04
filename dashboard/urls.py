# dashboard/urls.py

from django.urls import path
from . import views


app_name = 'dashboard'

urlpatterns = [
    path('vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/add-product/', views.vendor_add_product, name='vendor_add_product'),
    path('vendor/edit-product/<int:product_id>/', views.vendor_edit_product, name='vendor_edit_product'),
    path('vendor/delete-product/<int:pk>/', views.delete_product_application, name='delete_product_application'),
    path('vendor/product/<int:pk>/', views.vendor_product, name='vendor_product'),
    path('profile/', views.vendor_profile_view, name='vendor_profile_view'),
    path('profile/edit/', views.vendor_profile_edit, name='vendor_profile_edit'),
    path('my-orders/', views.vendor_my_orders, name='vendor_my_orders'),
]
