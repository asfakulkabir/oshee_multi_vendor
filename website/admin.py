# admin.py
from django.contrib import admin
from .models import *

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'for_mobile', 'created_at']
    list_filter = ['is_active', 'for_mobile']

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['id', 'image', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']