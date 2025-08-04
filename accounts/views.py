from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser
from accounts.models import CustomUser 
from accounts.forms import VendorRegistrationForm, LoginForm
from django.utils.crypto import get_random_string


class VendorRegistrationView(View):
    template_name = 'accounts/vendor_registration.html'

    def get(self, request, *args, **kwargs):
        form = VendorRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = VendorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            if not user.username:
                user.username = user.email
            user.vendor_status = 'pending'
            user.application_date = timezone.now()
            user.is_vendor = False  # <<-- Add this line!

            random_password = get_random_string(12)
            user.set_password(random_password)

            user.save()
            messages.success(request, 'Your vendor application has been submitted successfully! It is now pending approval.')
            return redirect('accounts:vendor_register')
        else:
            messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})
    
    
class UserLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')  # Already logged in
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.vendor_status == CustomUser.STATUS_APPROVED:
                    login(request, user)
                    messages.success(request, f"Welcome, {user.username}!")
                    return redirect('/')
                else:
                    messages.error(request, 'Your vendor account is not yet approved.')
            else:
                messages.error(request, 'Invalid username or password.')
        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class UserDashboardView(View):
    template_name = 'dashboard/vendor_dashboard.html'

    def get(self, request, *args, **kwargs):
        # Vendor info is directly on user model
        return render(request, self.template_name, {'user': request.user})


def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')
