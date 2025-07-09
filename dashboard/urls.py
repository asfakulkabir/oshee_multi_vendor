# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/add/', views.add_product, name='add_product'),
    path('vendor/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('vendor/delete/<int:pk>/', views.delete_product, name='delete_product'),
]
