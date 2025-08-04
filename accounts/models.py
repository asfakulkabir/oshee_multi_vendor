from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    is_vendor = models.BooleanField(default=False)
    
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    VENDOR_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # Vendor info (optional for normal users)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    contact_person_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    vendor_logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True)
    nid = models.CharField(max_length=50, blank=True, null=True)

    # Vendor application & approval status
    vendor_status = models.CharField(
        max_length=10,
        choices=VENDOR_STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Vendor application status"
    )
    application_date = models.DateTimeField(blank=True, null=True)
    approved_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Automatically set application date if vendor_status is pending and application_date is empty
        if self.vendor_status == self.STATUS_PENDING and not self.application_date:
            self.application_date = timezone.now()

        # Set approved_date if vendor_status changed to approved and approved_date not set
        if self.vendor_status == self.STATUS_APPROVED and not self.approved_date:
            self.approved_date = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_vendor_status_display()})"
