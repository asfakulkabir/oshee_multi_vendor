# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View
from .forms import VendorRegistrationForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class VendorRegistrationView(View):
    template_name = 'accounts/vendor_registration.html'

    def get(self, request, *args, **kwargs):
        form = VendorRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = VendorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            vendor_profile = form.save(commit=False)
            # Status defaults to 'pending' as per model, no need to set here
            vendor_profile.save()
            messages.success(request, 'Your vendor application has been submitted successfully! It is now pending approval.')
            return redirect('accounts:vendor_register') # Redirect to a success page or back to form
        else:
            messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})

class UserLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/') # Redirect authenticated users away from login page
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authenticate using our custom backend
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome, {user.username}!")
                return redirect('/') # Redirect to your home page or dashboard
            else:
                messages.error(request, 'Invalid email/phone number or password.')
        return render(request, self.template_name, {'form': form})

@method_decorator(login_required, name='dispatch')
class UserDashboardView(View):
    template_name = 'dashboard/vendor_dashboard.html' # You'll need to create this template

    def get(self, request, *args, **kwargs):
        # Example: show user's vendor profile if exists
        vendor_profile = None
        if hasattr(request.user, 'vendor_profile'):
            vendor_profile = request.user.vendor_profile
        return render(request, self.template_name, {'user': request.user, 'vendor_profile': vendor_profile})

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login') # Redirect to the login page
