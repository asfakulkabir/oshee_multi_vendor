from django.db import models
from django.contrib.auth import get_user_model
from products.models import DeliveryCharge

# -----------------------------
# Main Checkout Model
# -----------------------------
class Ecommercecheckouts(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()
    delivery_charge = models.ForeignKey(DeliveryCharge, on_delete=models.CASCADE, related_name='ecommercecheckouts')

    # Store list of items (JSON array)
    items_json = models.JSONField(default=list)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=255, choices=[
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], default='processing')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.customer_name}"


# -----------------------------
# Vendor Order Model
# -----------------------------
class VendorOrder(models.Model):
    ecommerce_checkout = models.ForeignKey(
        Ecommercecheckouts,
        on_delete=models.CASCADE,
        related_name='vendor_orders'
    )
    vendor = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='vendor_orders'
    )

    # Store only this vendor’s items
    items_json = models.JSONField(default=list)

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, default='processing')
    created_at = models.DateTimeField(auto_now_add=True)
    # New fields for customer info
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Vendor Order for {self.vendor.username} from Checkout {self.ecommerce_checkout.id}"
