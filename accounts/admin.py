from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'vendor_status', 'is_staff', 'is_active')
    list_filter = ('vendor_status', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Vendor Info', {
            'fields': (
                'company_name',
                'contact_person_name',
                'phone_number',
                'address',
                'business_type',
                'website_url',
                'tax_id',
                'vendor_logo',
                'nid',
                'vendor_status',
                'application_date',
                'approved_date',
            )
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)
