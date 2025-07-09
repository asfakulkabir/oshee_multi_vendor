from django.db import models
from products.models import *

# Create your models here.
class Ecommercecheckouts(models.Model):
    items_json  = models.CharField(max_length=1000, default="{}")
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()
    delivery_charge = models.ForeignKey(DeliveryCharge, on_delete=models.CASCADE, related_name='ecommercecheckouts')
    total_amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=[
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ])
    def __str__(self):
        return f"Order {self.id} by {self.customer_name}"