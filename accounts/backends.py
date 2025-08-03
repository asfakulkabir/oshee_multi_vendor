# accounts/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrPhoneNumberBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        try:
            # Try to find user by email (either in the username field or email field)
            user = UserModel.objects.get(Q(username=username) | Q(email=username))
        except UserModel.DoesNotExist:
            user = None

        if user is None:
            # If not found by email, try to find by phone number via VendorProfile.
            try:
                from accounts.models import VendorProfile 
                vendor_profile = VendorProfile.objects.get(phone_number=username, user__isnull=False)
                user = vendor_profile.user # Get the associated User
            except VendorProfile.DoesNotExist:
                return None # User not found by email or phone number

        # If a user is found by either method, check the password
        if user and user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        """
        Required for Django's authentication system.
        Retrieves a user instance by their primary key.
        """
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
