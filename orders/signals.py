from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ecommercecheckouts, VendorOrder
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=Ecommercecheckouts)
def create_vendor_orders(sender, instance, created, **kwargs):
    if not created:
        return

    items = instance.items_json
    vendor_items_map = {}

    for item in items:
        vendor_id = item.get('vendor_id')
        if vendor_id:
            vendor_id = int(vendor_id)
            vendor_items_map.setdefault(vendor_id, []).append(item)

    for vendor_id, vendor_items in vendor_items_map.items():
        try:
            vendor = User.objects.get(id=vendor_id)
            total_price = sum(
                item.get('price', 0) * item.get('quantity', 1)
                for item in vendor_items
            )

            VendorOrder.objects.create(
                vendor=vendor,
                ecommerce_checkout=instance,
                items_json=vendor_items,
                total_price=total_price,
                customer_name=instance.customer_name,
                customer_phone=instance.customer_phone,
                customer_address=instance.customer_address,
            )
        except User.DoesNotExist:
            continue
