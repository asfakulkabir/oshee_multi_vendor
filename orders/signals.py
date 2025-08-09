from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from django.contrib.auth import get_user_model
from decimal import Decimal

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
                delivery_charge=instance.delivery_charge,
            )
        except User.DoesNotExist:
            continue


@receiver(post_save, sender=VendorOrder)
def update_vendor_financial_summary(sender, instance, created, **kwargs):
    # Only act when the order is marked as delivered and not already recorded
    if instance.status == 'delivered' and not VendorFinancialTransaction.objects.filter(order=instance).exists():
        # Get or create the financial summary for this vendor
        summary, _ = VendorFinancialSummary.objects.get_or_create(vendor=instance.vendor)

        # Collect vendor products
        vendor_products = {str(v.id): v for v in instance.vendor.vendor_products.all()}
        vendor_amount = Decimal('0.00')

        # Calculate vendor amount
        for item in instance.items_json:
            item_quantity = int(item.get('quantity', 0))
            item_product_id = item.get('product_id')
            try:
                vendor_product = vendor_products[str(item_product_id)]
                vendor_price = Decimal(str(vendor_product.vendor_price))
                vendor_amount += vendor_price * item_quantity
            except (KeyError, TypeError):
                pass

        # Calculate total and admin amounts
        try:
            total_price = Decimal(str(instance.total_price))
        except (ValueError, TypeError):
            total_price = Decimal('0.00')

        admin_amount = total_price - vendor_amount

        # Update the summary
        summary.total_revenue += total_price
        summary.total_vendor_amount += vendor_amount
        summary.total_admin_amount += admin_amount
        summary.save()

        # Create a financial transaction
        VendorFinancialTransaction.objects.create(
            summary=summary,
            vendor=instance.vendor,
            order=instance,
            order_price=total_price,
            admin_amount=admin_amount,
            vendor_amount=vendor_amount
        )