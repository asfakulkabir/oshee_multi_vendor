from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone

class VendorProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    company_name = models.CharField(max_length=255)
    contact_person_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField()
    business_type = models.CharField(max_length=100, blank=True)
    website_url = models.URLField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    vendor_logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True)
    nid = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )
    application_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(blank=True, null=True)

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_profile',
    )

    class Meta:
        verbose_name = "Vendor Application"
        verbose_name_plural = "Vendor Applications"
        ordering = ['-application_date']

    def __str__(self):
        return f"{self.company_name} ({self.get_status_display()})"


@receiver(pre_save, sender=VendorProfile)
def track_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = VendorProfile.objects.get(pk=instance.pk)
            instance._status_changed_to_approved = old_instance.status != 'approved' and instance.status == 'approved'
        except VendorProfile.DoesNotExist:
            instance._status_changed_to_approved = instance.status == 'approved'
    else:
        instance._status_changed_to_approved = instance.status == 'approved'


@receiver(post_save, sender=VendorProfile)
def create_user_on_vendor_approval(sender, instance, created, **kwargs):
    status_changed_to_approved = getattr(instance, '_status_changed_to_approved', False)

    if status_changed_to_approved and instance.user is None:
        initial_password = str(uuid.uuid4())[:12]
        try:
            user = User.objects.create_user(
                username=instance.email,
                email=instance.email,
                password=initial_password,
                first_name=instance.contact_person_name.split(' ')[0] if instance.contact_person_name else '',
                last_name=' '.join(instance.contact_person_name.split(' ')[1:]) if instance.contact_person_name and ' ' in instance.contact_person_name else '',
                is_active=True
            )
            instance.user = user
            instance.approved_date = timezone.now()
            instance.save(update_fields=['user', 'approved_date'])
        except Exception as e:
            pass # In a production environment, log this error formally
