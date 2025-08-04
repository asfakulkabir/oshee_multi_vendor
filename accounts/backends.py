from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class VendorApprovedBackend(ModelBackend):
    """
    Allows login only if user is active AND:
    - If user is a vendor, vendor_status must be 'approved'
    - Otherwise, allow login
    """

    def user_can_authenticate(self, user):
        is_active = super().user_can_authenticate(user)
        if not is_active:
            return False

        # If vendor_status field exists, check approval
        if hasattr(user, 'vendor_status'):
            if user.vendor_status == 'pending' or user.vendor_status == 'rejected':
                return False
        return True
