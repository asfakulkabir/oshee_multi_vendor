import os
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from django.conf import settings
from django.core.files import File
from django.db import transaction 

from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from .models import *

from django.contrib.auth import get_user_model
User = get_user_model() 


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_thumbnail', 'name', 'alt_text', 'is_featured', 'order', 'image')
    readonly_fields = ('image_thumbnail',)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    image_thumbnail.short_description = "Thumbnail"


class ProductVariationInline(admin.TabularInline): 
    model = ProductVariation
    extra = 1
    fields = ('size', 'weight', 'color', 'price', 'stock')


class CategoryResource(resources.ModelResource):
    parent = fields.Field(
        column_name='parent_name',
        attribute='parent',
        widget=ForeignKeyWidget(Category, 'name')
    )

    def dehydrate_parent(self, obj):
        return obj.parent.name if obj.parent else ''

    def before_import_row(self, row, **kwargs):
        parent_name = row.get('parent_name')
        if parent_name:
            Category.objects.get_or_create(name=parent_name)
        
    class Meta:
        model = Category
        import_id_fields = ('slug',)
        fields = ('name', 'slug', 'parent', 'group_name', 'image')
        export_order = ('name', 'slug', 'parent', 'group_name', 'image')
        skip_unchanged = True


class ProductImageResource(resources.ModelResource):
    product = fields.Field(
        column_name='product_slug',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'slug')
    )
    image_path = fields.Field(
        column_name='image_path',
        attribute='image',
        readonly=False 
    )

    def dehydrate_image_path(self, product_image):
        if product_image.image:
            return product_image.image.name 
        return ''

    def before_import_row(self, row, **kwargs):
        image_file_path = row.get('image_path', '').strip()
        self._current_image_abs_path = None
        self._current_image_filename = None

        if image_file_path:
            abs_path = os.path.join(settings.MEDIA_ROOT, image_file_path)
            if os.path.exists(abs_path):
                self._current_image_abs_path = abs_path
                self._current_image_filename = os.path.basename(abs_path)
            else:
                self.errors.append(f"Image file not found at {abs_path} for row: {row}")
                row['image_path'] = None 

    def after_import_instance(self, instance, new, **kwargs):
        if self._current_image_abs_path and self._current_image_filename:
            try:
                with open(self._current_image_abs_path, 'rb') as f:
                    instance.image.save(self._current_image_filename, File(f, name=self._current_image_filename), save=False)
                    instance.save(update_fields=['image']) 
            except Exception as e:
                self.errors.append(f"Error saving image '{self._current_image_filename}' for ProductImage ID {instance.id}: {e}")
        elif not instance.image and instance.pk and 'image_path' in kwargs['row'] and not kwargs['row']['image_path']:
            if instance.image:
                instance.image.delete(save=False)
                instance.image = None
                instance.save(update_fields=['image'])

    class Meta:
        model = ProductImage
        import_id_fields = ('product', 'name')
        fields = ('product', 'name', 'alt_text', 'is_featured', 'order', 'image_path')
        export_order = ('product', 'name', 'alt_text', 'is_featured', 'order', 'image_path')
        skip_unchanged = True


class ProductVariationResource(resources.ModelResource):
    product = fields.Field(
        column_name='product_slug',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'slug')
    )

    class Meta:
        model = ProductVariation
        import_id_fields = ('product', 'size', 'weight', 'color') 
        fields = ('product', 'size', 'weight', 'color', 'price', 'stock')
        export_order = ('product', 'size', 'weight', 'color', 'price', 'stock')
        skip_unchanged = True


class ProductResource(resources.ModelResource):
    vendor = fields.Field(
        column_name='vendor_username',
        attribute='vendor',
        widget=ForeignKeyWidget(User, 'username') 
    )
    categories = fields.Field(
        column_name='category_names',
        attribute='categories',
        widget=ManyToManyWidget(Category, field='name', separator='|') 
    )

    exported_images = fields.Field(column_name='exported_images', readonly=True)
    exported_variations = fields.Field(column_name='exported_variations', readonly=True)

    def dehydrate_exported_images(self, product):
        return '|'.join([
            f"{img.name or 'Unnamed'}:{img.image.name if img.image else ''}:{img.alt_text or ''}:{int(img.is_featured)}:{img.order}"
            for img in product.images.all()
        ])

    def dehydrate_exported_variations(self, product):
        return '|'.join([
            f"{var.size or ''}:{var.weight or ''}:{var.color or ''}:{var.price or ''}:{var.stock or ''}"
            for var in product.variations.all()
        ])

    def before_import(self, dataset, using_transactions=None, dry_run=None, **kwargs):
        self._row_data_by_slug = {}
        for row in dataset.dict:
            slug = row.get('slug')
            if slug:
                self._row_data_by_slug[slug] = row

    def before_import_row(self, row, **kwargs):
        category_names = row.get("category_names", "")
        for name in category_names.split("|"):
            name = name.strip()
            if name:
                Category.objects.get_or_create(name=name)

        vendor_username = row.get("vendor_username")
        if vendor_username:
            User.objects.get_or_create(username=vendor_username)

    @transaction.atomic 
    def after_import_instance(self, instance, new, **kwargs):
        row_data = self._row_data_by_slug.get(instance.slug)
        if not row_data:
            return 

        images_data_str = row_data.get('exported_images', '')
        if images_data_str:
            instance.images.all().delete() 
            for image_entry in images_data_str.split('|'):
                parts = image_entry.split(':')
                if len(parts) < 5: 
                    continue

                img_name, rel_path, alt_text, is_featured_str, order_str = [p.strip() for p in parts[:5]]
                
                is_featured = bool(int(is_featured_str)) if is_featured_str.isdigit() else False
                order = int(order_str) if order_str.isdigit() else 0

                abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                
                if os.path.exists(abs_path):
                    try:
                        with open(abs_path, 'rb') as f:
                            filename = os.path.basename(abs_path)
                            ProductImage.objects.create(
                                product=instance,
                                image=File(f, name=filename),
                                name=img_name if img_name != 'Unnamed' else None, 
                                alt_text=alt_text if alt_text != 'Unnamed' else None,
                                is_featured=is_featured,
                                order=order
                            )
                    except Exception as e:
                        self.errors.append(f"Error saving image '{rel_path}' for product '{instance.slug}': {e}")
                else:
                    self.errors.append(f"Image file not found at '{abs_path}' for product '{instance.slug}'")

        variations_data_str = row_data.get('exported_variations', '')
        if variations_data_str and instance.product_type == Product.VARIABLE:
            instance.variations.all().delete() 
            for variation_entry in variations_data_str.split('|'):
                parts = variation_entry.split(':')
                if len(parts) < 5: 
                    continue

                size, weight, color, price_str, stock_str = [p.strip() for p in parts[:5]]

                price = float(price_str) if price_str else None
                stock = int(stock_str) if stock_str.isdigit() else 0 

                try:
                    ProductVariation.objects.create(
                        product=instance,
                        size=size if size else None,
                        weight=weight if weight else None,
                        color=color if color else None,
                        price=price,
                        stock=stock,
                    )
                except Exception as e:
                    self.errors.append(f"Error creating variation '{variation_entry}' for product '{instance.slug}': {e}")
        elif instance.product_type == Product.SIMPLE:
            instance.variations.all().delete()

    class Meta:
        model = Product
        import_id_fields = ('slug',)
        fields = (
            'name', 'slug', 'short_description', 'description',
            'product_type', 'vendor', 'categories',
            'regular_price', 'sale_price', 'stock_quantity',
            'is_active', 'is_featured', 'seo_title', 'meta_description',
            'created_at', 'updated_at',
            'exported_images', 'exported_variations', 
            'vendor_username', 'category_names' 
        )
        export_order = (
            'name', 'slug', 'short_description', 'description',
            'product_type', 'vendor_username', 'category_names',
            'regular_price', 'sale_price', 'stock_quantity',
            'is_active', 'is_featured', 'seo_title', 'meta_description',
            'created_at', 'updated_at',
            'exported_images', 'exported_variations',
        )
        skip_unchanged = True


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    inlines = [ProductImageInline, ProductVariationInline]
    list_display = (
        'name_display', 'vendor_display', 'product_type', 'get_display_price',
        'stock_quantity_display', 'is_active', 'is_featured', 'created_at'
    )
    list_filter = ('product_type', 'is_active', 'is_featured', 'vendor', 'categories')
    search_fields = ('name', 'vendor__username', 'short_description', 'description') 
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('categories',) 

    def name_display(self, obj):
        return obj.name or "---"
    name_display.short_description = "Name"

    def vendor_display(self, obj):
        return obj.vendor.username if obj.vendor else "---"
    vendor_display.short_description = "Vendor"

    def stock_quantity_display(self, obj):
        if obj.product_type == Product.SIMPLE:
            return obj.stock_quantity if obj.stock_quantity is not None else "---"
        else: 
            total_stock = obj.variations.aggregate(Sum('stock'))['stock__sum']
            return total_stock if total_stock is not None else "---"
    stock_quantity_display.short_description = "Stock"

    def get_display_price(self, obj):
        price = obj.get_display_price()
        return f"৳{price:.2f}" if price is not None else "---"
    get_display_price.short_description = "Price"

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'product_type', 'vendor', 'categories'),
        }),
        ('Pricing & Inventory', {
            'fields': ('regular_price', 'sale_price', 'stock_quantity'), 
            'description': 'For "Simple" products, use "Stock Quantity". For "Variable" products, stock is managed per variation below.'
        }),
        ('Description', {
            'fields': ('short_description', 'description'),
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured'),
        }),
        ('SEO Options', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'meta_description'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ProductVariation)
class ProductVariationAdmin(ImportExportModelAdmin):
    resource_class = ProductVariationResource
    list_display = ('product_display', 'size_display', 'color_display', 'weight_display', 'price_display', 'stock_display')
    list_filter = ('product__product_type', 'product')
    search_fields = ('product__name', 'size', 'color', 'weight')

    def product_display(self, obj):
        return obj.product.name if obj.product else "---"
    product_display.short_description = "Product"

    def size_display(self, obj):
        return obj.size or "---"
    size_display.short_description = "Size"

    def color_display(self, obj):
        return obj.color or "---"
    color_display.short_description = "Color"

    def weight_display(self, obj):
        return obj.weight or "---"
    weight_display.short_description = "Weight"

    def price_display(self, obj):
        return f"৳{obj.price:.2f}" if obj.price is not None else "---"
    price_display.short_description = "Price"

    def stock_display(self, obj):
        return obj.stock if obj.stock is not None else "---"
    stock_display.short_description = "Stock"


@admin.register(ProductImage)
class ProductImageAdmin(ImportExportModelAdmin):
    resource_class = ProductImageResource
    list_display = ('product_display', 'name_display', 'image_thumbnail', 'is_featured', 'order')
    list_filter = ('product__name', 'is_featured')
    search_fields = ('product__name', 'name', 'alt_text')
    readonly_fields = ('image_thumbnail',)

    def product_display(self, obj):
        return obj.product.name if obj.product else "---"
    product_display.short_description = "Product"

    def name_display(self, obj):
        return obj.name or "---"
    name_display.short_description = "Name"

    def image_thumbnail(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" width="50" height="auto" style="object-fit: contain; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    image_thumbnail.short_description = "Thumbnail"


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_class = CategoryResource
    list_display = ('name_display', 'parent_display', 'slug_display', 'group_name_display', 'image_thumbnail', 'view_on_site_link')
    list_filter = ('parent', 'group_name',)
    search_fields = ('name', 'slug', 'group_name')
    prepopulated_fields = {"slug": ("name",)}

    def name_display(self, obj):
        return obj.name or "---"
    name_display.short_description = "Name"

    def parent_display(self, obj):
        return obj.parent.name if obj.parent and obj.parent.name else "---"
    parent_display.short_description = "Parent"

    def slug_display(self, obj):
        return obj.slug or "---"
    slug_display.short_description = "Slug"

    def group_name_display(self, obj):
        return obj.group_name or "---"
    group_name_display.short_description = "Group Name"
    
    def image_thumbnail(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    image_thumbnail.short_description = "Image"

    def view_on_site_link(self, obj):
        try:
            return format_html('<a href="{}" target="_blank">View on Site</a>', obj.get_absolute_url())
        except Exception: 
            return "N/A"
    view_on_site_link.short_description = "Frontend URL"

@admin.register(DeliveryCharge)
class DeliveryChargeAdmin(admin.ModelAdmin):
    list_display = ('zone', 'charge')
    search_fields = ('zone',)
    list_filter = ('zone',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['zone']
        return super().get_readonly_fields(request, obj)