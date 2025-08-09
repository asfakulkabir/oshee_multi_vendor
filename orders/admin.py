from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from django.core.exceptions import ObjectDoesNotExist
import json

from .models import Ecommercecheckouts, VendorOrder, VendorFinancialSummary, VendorFinancialTransaction
from products.models import DeliveryCharge
from accounts.models import CustomUser
from django.contrib.auth import get_user_model
User = get_user_model()

# Resource for import/export
class EcommercecheckoutsResource(resources.ModelResource):
    ordered_items = fields.Field(attribute='items_json', column_name='Ordered Products')
    delivery_charge_name = fields.Field(attribute='delivery_charge__zone', column_name='Delivery Location')

    class Meta:
        model = Ecommercecheckouts
        fields = (
            'id',
            'customer_name',
            'customer_phone',
            'customer_address',
            'delivery_charge_name',
            'total_amount',
            'status',
            'created_at',
            'ordered_items'
        )
        export_order = (
            'id',
            'customer_name',
            'customer_phone',
            'customer_address',
            'delivery_charge_name',
            'total_amount',
            'status',
            'created_at',
            'ordered_items'
        )

    def dehydrate_ordered_items(self, checkout):
        try:
            items = checkout.items_json  # Already a list from JSONField
            if not items:
                return "No items"
            item_strings = []
            for item in items:
                name = item.get('name', 'N/A')
                price = item.get('price', 0)
                quantity = item.get('quantity', 0)
                variation_data = item.get('variation', {})
                variation_display = ', '.join(f'{k}: {v}' for k, v in variation_data.items()) if variation_data else 'None'
                vendor_id = item.get('vendor_id')
                vendor_name = "N/A"
                if vendor_id:
                    try:
                        vendor = User.objects.get(id=vendor_id)
                        vendor_name = getattr(vendor, 'company_name', vendor.username)
                    except ObjectDoesNotExist:
                        vendor_name = "Vendor not found"
                item_strings.append(f"{name} (Qty: {quantity}, Price: {price}৳, Variation: {variation_display}, Vendor: {vendor_name})")
            return "; ".join(item_strings)
        except Exception as e:
            return f"Error: {e}"

# Admin form with JSON validation
class EcommercecheckoutsForm(forms.ModelForm):
    class Meta:
        model = Ecommercecheckouts
        fields = '__all__'
        widgets = {
            'items_json': forms.Textarea(attrs={'rows': 4, 'cols': 70}),
        }

    def clean_items_json(self):
        items_json = self.cleaned_data.get('items_json')

        # If it's a string, try to parse it
        if isinstance(items_json, str):
            try:
                return json.loads(items_json)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for items.")

        # If it's already a list or dict (valid JSONField content), return as is
        elif isinstance(items_json, (list, dict)):
            return items_json

        raise forms.ValidationError("Invalid data type for items_json.")


# Main Admin Class
@admin.register(Ecommercecheckouts)
class EcommercecheckoutsAdmin(ImportExportModelAdmin):
    resource_class = EcommercecheckoutsResource
    form = EcommercecheckoutsForm

    list_display = (
        'id',
        'customer_name',
        'customer_phone',
        'total_amount_display',
        'delivery_charge_link',
        'status',
        'created_at',
        'view_items_json_summary',
    )
    list_filter = ('status', 'created_at', 'delivery_charge')
    search_fields = ('customer_name', 'customer_phone', 'customer_address')
    ordering = ('-created_at',)
    readonly_fields = ('total_amount_display', 'created_at', 'view_items_table_detail',)

    fieldsets = (
        (None, {
            'fields': (('customer_name', 'customer_phone'), 'customer_address', 'delivery_charge', 'total_amount_display', 'status', 'created_at',)
        }),
        ('Ordered Products Details', {
            'fields': ('view_items_table_detail',),
            'description': 'Details of products in this order.',
        }),
        ('Raw Data (Advanced)', {
            'fields': ('items_json',),
            'classes': ('collapse',),
        }),
    )

    def total_amount_display(self, obj):
        return f'{obj.total_amount} ৳'
    total_amount_display.short_description = "Total Amount"

    def delivery_charge_link(self, obj):
        if obj.delivery_charge:
            app_label = obj.delivery_charge._meta.app_label
            model_name = obj.delivery_charge._meta.model_name
            try:
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.delivery_charge.pk])
                return format_html('<a href="{}">{}</a>', url, obj.delivery_charge.zone)
            except Exception:
                return f"{obj.delivery_charge.zone}"
        return "N/A"
    delivery_charge_link.short_description = "Delivery Area"

    def view_items_json_summary(self, obj):
        try:
            items = obj.items_json
            if not items:
                return "No items"
            summary_parts = [f"{item.get('name', 'Product')} (x{item.get('quantity', 1)})" for item in items]
            return ", ".join(summary_parts[:3]) + ("..." if len(summary_parts) > 3 else "")
        except Exception:
            return format_html('<span style="color: red;">Error</span>')
    view_items_json_summary.short_description = "Products Summary"

    def view_items_table_detail(self, obj):
        try:
            return self.create_items_table_html(obj.items_json)
        except Exception as e:
            return format_html(f'<p style="color: red;">Error displaying items: {e}</p>')
    view_items_table_detail.short_description = "Ordered Products"

    def create_items_table_html(self, items):
        vendor_ids = [item.get('vendor_id') for item in items if item.get('vendor_id')]
        vendors = User.objects.filter(id__in=vendor_ids)
        vendor_dict = {
            str(v.id): getattr(v, 'company_name', v.username or f"Vendor {v.id}")
            for v in vendors
        }

        table_html = """
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px;">Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Image</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Price</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Qty</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Variation</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Subtotal</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Vendor</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in items:
            name = item.get("name", "N/A")
            image_url = item.get("image", "/static/icons/default-image.webp")
            if image_url and not image_url.startswith(('http', '/media/')):
                image_url = f"/media/{image_url}"
            price = float(item.get("price", 0))
            qty = int(item.get("quantity", 0))
            variation = item.get('variation', {})
            variation_display = ', '.join(f'{k}: {v}' for k, v in variation.items()) if variation else 'N/A'
            subtotal = price * qty
            vendor_id = str(item.get('vendor_id'))
            vendor_name = vendor_dict.get(vendor_id, 'Vendor not found')

            table_html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">
                        <img src="{image_url}" width="50" height="50" style="object-fit: cover; border-radius: 4px;">
                    </td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{price:.2f} ৳</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{qty}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{variation_display}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{subtotal:.2f} ৳</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{vendor_name}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        return format_html(table_html)

@admin.register(VendorOrder)
class VendorOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'vendor_company_name',
        'ecommerce_checkout',
        'delivery_charge',
        'total_price',
        'status',
        'created_at',
        'summary'
    ]
    readonly_fields = ['created_at', 'view_items_table']

    def vendor_company_name(self, obj):
        return obj.vendor.company_name if obj.vendor else "-"
    vendor_company_name.short_description = "Vendor"

    def summary(self, obj):
        items = obj.items_json
        return ", ".join(f"{i.get('name')} (x{i.get('quantity')})" for i in items)
    summary.short_description = "Items"

    def view_items_table(self, obj):
        items = obj.items_json
        table_html = """
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px;">Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Image</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Price</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Qty</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Subtotal</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Variation</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in items:
            name = item.get("name", "N/A")
            image_url = item.get("image", "/static/icons/default-image.webp")
            if image_url and not image_url.startswith(('http://', 'https://', '/media/')):
                image_url = f"/media/{image_url}"
            price = item.get("price", 0)
            qty = item.get("quantity", 0)
            subtotal = price * qty
            variation = item.get("variation", {})
            variation_display = ', '.join(f'{k}: {v}' for k, v in variation.items()) or "N/A"

            table_html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">
                        <img src="{image_url}" width="50" height="50" style="object-fit: cover; border-radius: 4px;">
                    </td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{price:.2f} ৳</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{qty}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{subtotal:.2f} ৳</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{variation_display}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        from django.utils.html import format_html
        return format_html(table_html)

    view_items_table.short_description = "Item Breakdown"

# vendor financial statement 
# --- Resources for Export ---

class VendorFinancialSummaryResource(resources.ModelResource):
    class Meta:
        model = VendorFinancialSummary
        # Use the vendor's company name field and a date field.
        # Assuming your User model has a field named 'vendor_companyname'.
        fields = ('id', 'vendor__company_name', 'total_revenue', 'total_vendor_amount', 'total_admin_amount')
        export_order = ('id', 'vendor__company_name', 'total_revenue', 'total_vendor_amount', 'total_admin_amount')

class VendorFinancialTransactionResource(resources.ModelResource):
    class Meta:
        model = VendorFinancialTransaction
        # Use the vendor's company name field and the transaction date.
        fields = ('id', 'vendor__company_name', 'transaction_date', 'order__id', 'order_price', 'vendor_amount', 'admin_amount')
        export_order = ('id', 'vendor__company_name', 'transaction_date', 'order__id', 'order_price', 'vendor_amount', 'admin_amount')

# --- Admin Classes with Export ---
class VendorFinancialTransactionInline(admin.TabularInline):
    model = VendorFinancialTransaction
    extra = 0
    readonly_fields = (
        'order',
        'transaction_date',
        'order_price',
        'vendor_amount',
        'admin_amount',
    )
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(VendorFinancialSummary)
class VendorFinancialSummaryAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = VendorFinancialSummaryResource
    list_display = (
        'vendor_company_name',
        'total_revenue',
        'total_vendor_amount',
        'total_admin_amount',
    )
    search_fields = ('vendor__username', 'vendor__company_name')
    list_filter = ('vendor__company_name',)
    readonly_fields = (
        'vendor_company_name',
        'total_revenue',
        'total_vendor_amount',
        'total_admin_amount',
    )
    inlines = [VendorFinancialTransactionInline]

    def vendor_company_name(self, obj):
        return obj.vendor.company_name
    vendor_company_name.short_description = "Vendor Company Name"

    def has_add_permission(self, request):
        return False
    
@admin.register(VendorFinancialTransaction)
class VendorFinancialTransactionAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = VendorFinancialTransactionResource
    list_display = (
        'vendor_company_name',
        'order',
        'transaction_date',
        'order_price',
        'vendor_amount',
        'admin_amount',
    )
    list_filter = ('vendor__company_name', 'transaction_date')
    search_fields = ('vendor__username', 'vendor__company_name', 'order__id')
    readonly_fields = (
        'vendor_company_name',
        'order',
        'transaction_date',
        'order_price',
        'vendor_amount',
        'admin_amount',
    )
    ordering = ('-transaction_date',)

    def vendor_company_name(self, obj):
        return obj.vendor.company_name
    vendor_company_name.short_description = "Vendor Company Name"

    def has_add_permission(self, request):
        return False
