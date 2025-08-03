from django.urls import path, include
from . import views
from .views import *

app_name = 'accounts'

urlpatterns = [
    path('register/', VendorRegistrationView.as_view(), name='vendor_register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
    # Add a simple home view for testing redirects
    path('', UserDashboardView.as_view(), name='home'), # This will be the default after login
]
