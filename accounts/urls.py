# accounts/urls.py
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordResetForm
from .views import *

app_name = 'accounts'

urlpatterns = [
    # Authentication Views
    path('register/', VendorRegistrationView.as_view(), name='vendor_register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),

    # Password Reset Views
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        form_class=CustomPasswordResetForm,
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
        # Change Password View
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change_form.html',
        success_url=reverse_lazy('accounts:password_change_done')
    ), name='password_change'),
    
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),

    
    # Dashboard
    path('', UserDashboardView.as_view(), name='home'),
]