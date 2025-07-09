from django.contrib import admin
from .models import Ecommercecheckouts
from products.models import DeliveryCharge
import json
from django.utils.html import format_html
from django import forms
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import JSONWidget
from django.urls import reverse


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
        export_order = fields

    def dehydrate_ordered_items(self, checkout):
        try:
            items = json.loads(checkout.items_json)
            if not items:
                return "No items"

            item_strings = []
            for item in items:
                name = item.get('name', 'N/A')
                price = item.get('price', 0)
                quantity = item.get('quantity', 0)
                variation_data = item.get('variation', {})
                variation_display = ', '.join(f'{k}: {v}' for k, v in variation_data.items()) if variation_data else 'None'
                item_strings.append(f"{name} (Qty: {quantity}, Price: {price}৳, Variation: {variation_display})")
            return "; ".join(item_strings)
        except json.JSONDecodeError:
            return "Invalid items JSON"
        except Exception as e:
            return f"Error processing items: {e}"

class EcommercecheckoutsForm(forms.ModelForm):
    class Meta:
        model = Ecommercecheckouts
        fields = '__all__'
        widgets = {
            'items_json': forms.Textarea(attrs={'rows': 4, 'cols': 70}),
        }

    def clean_items_json(self):
        items_json = self.cleaned_data.get('items_json')
        if items_json:
            try:
                json.loads(items_json)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for items.")
        return items_json

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
        'view_items_json_summary'
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
    total_amount_display.short_description = "Calculated Total Amount"

    def delivery_charge_link(self, obj):
        if obj.delivery_charge:
            app_label = obj.delivery_charge._meta.app_label
            model_name = obj.delivery_charge._meta.model_name
            url_name = f'admin:{app_label}_{model_name}_change'

            try:
                url = reverse(url_name, args=[obj.delivery_charge.pk])
                return format_html('<a href="{}">{}</a>', url, obj.delivery_charge.zone)
            except Exception as e:
                return f"Error: {obj.delivery_charge.zone} (ID: {obj.delivery_charge.pk})"
        return "N/A"
    delivery_charge_link.short_description = "Delivery Area"

    def view_items_json_summary(self, obj):
        try:
            items = json.loads(obj.items_json)
            if not items:
                return "No items"
            summary_parts = []
            for item in items:
                name = item.get('name', 'Product')
                qty = item.get('quantity', 1)
                summary_parts.append(f"{name} (x{qty})")
            return ", ".join(summary_parts[:3]) + ("..." if len(summary_parts) > 3 else "")
        except json.JSONDecodeError:
            return format_html('<span style="color: red;">Invalid JSON</span>')
        except Exception:
            return "Error"
    view_items_json_summary.short_description = "Products Summary"
    view_items_json_summary.allow_tags = True


    def view_items_table_detail(self, obj):
        try:
            items = json.loads(obj.items_json)
            return self.create_items_table_html(items)
        except json.JSONDecodeError:
            return format_html('<p style="color: red;">Error: Invalid JSON format for items.</p>')
        except Exception as e:
            return format_html(f'<p style="color: red;">Error displaying items: {e}</p>')

    view_items_table_detail.short_description = "Ordered Products"
    view_items_table_detail.allow_tags = True


    def create_items_table_html(self, items):
        table_html = """
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Image</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Price</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Quantity</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Variation</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Subtotal</th>
                </tr>
            </thead>
            <tbody>
        """

        for item in items:
            item_name = item.get("name", "N/A")
            item_image_url = item.get("image", "")
            item_price = item.get("price", 0)
            item_quantity = item.get("quantity", 0)

            if item_image_url and not item_image_url.startswith(('http://', 'https://', '/media/')):
                item_image_url = f'/media/{item_image_url}'
            elif not item_image_url:
                item_image_url = '/static/icons/default-image.webp'

            variation_data = item.get('variation', {})
            variation_display = ', '.join(f'{key}: {value}' for key, value in variation_data.items() if value) if variation_data else 'N/A'

            subtotal = item_price * item_quantity

            table_html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{item_name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">
                        <img src="{item_image_url}" width="50" height="50" style="object-fit: cover; border-radius: 4px;">
                    </td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{item_price:.2f} ৳</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{item_quantity}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{variation_display}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{subtotal:.2f} ৳</td>
                </tr>
            """
        table_html += """
            </tbody>
        </table>
        """
        return format_html(table_html)