# admin.py
from django.contrib import admin
from .models import *
from django.utils.html import format_html


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'for_mobile', 'created_at']
    list_filter = ['is_active', 'for_mobile']

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['id', 'image', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']

@admin.register(HomeComponents)
class HomeComponentsAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'image_tag')
    list_filter = ('category',)
    search_fields = ('title',)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />'.format(obj.image.url))
        return "No Image"

    image_tag.short_description = 'Image'