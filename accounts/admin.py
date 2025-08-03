# accounts/admin.py
from django.contrib import admin
from .models import VendorProfile

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'email', 'phone_number', 'status', 'application_date', 'user_linked')
    list_filter = ('status', 'application_date')
    search_fields = ('company_name', 'email', 'phone_number', 'contact_person_name')
    readonly_fields = ('application_date', 'approved_date', 'user') # User and dates are set by system/signal
    fieldsets = (
        (None, {
            'fields': ('company_name', 'contact_person_name', 'email', 'phone_number', 'address', 'business_type', 'website_url', 'tax_id', 'vendor_logo', 'nid')
        }),
        ('Application Status', {
            'fields': ('status', 'application_date', 'approved_date', 'user')
        }),
    )

    def user_linked(self, obj):
        return bool(obj.user)
    user_linked.boolean = True
    user_linked.short_description = 'User Created?'
