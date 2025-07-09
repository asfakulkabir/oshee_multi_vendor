import os 
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from ckeditor.fields import RichTextField
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True, blank=True, null=True, verbose_name=_("Category Name"))
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name=_("Parent Category"))
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True, verbose_name=_("Category Slug"))
    group_name = models.CharField(max_length=100, blank=True, null=True, help_text=_("A way to group categories (e.g., 'Gender', 'Brand', 'Department')"))
    image = models.ImageField(upload_to='category_images/', blank=True, null=True, verbose_name=_("Category Image"))
    
    def get_full_slug(self):
        slugs = []
        category = self
        while category:
            slugs.insert(0, category.slug)
            category = category.parent
        return '/'.join(slugs)
    

    def save(self, *args, **kwargs):
        if self.name == '':
            self.name = None
        if self.slug == '':
            self.slug = None

        if self.name and not self.slug:
            base_slug = slugify(self.name)
            temp_slug = base_slug
            counter = 1
            while Category.objects.filter(slug=temp_slug).exclude(pk=self.pk).exists():
                temp_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = temp_slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or f"Unnamed Category ({self.id})"

    def get_absolute_url(self):
        full_slug = self.get_full_slug()
        if full_slug:
            return reverse('category_detail', kwargs={'full_slug': full_slug})
        return reverse('category_detail', kwargs={'slug': self.slug})


    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['group_name', 'name']



class Product(models.Model):
    SIMPLE = 'simple'
    VARIABLE = 'variable'

    PRODUCT_TYPE_CHOICES = [
        (SIMPLE, 'Simple'),
        (VARIABLE, 'Variable'),
    ]
    vendor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255, blank=True, null=True) 
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True, null=True) 
    short_description = RichTextField(blank=True, null=True) 
    description = RichTextField(blank=True, null=True) 
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default=SIMPLE, blank=True, null=True) 
    categories = models.ManyToManyField(Category, blank=True, related_name='products') 
    
    regular_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)], blank=True, null=True) 
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)])
    
    stock_quantity = models.PositiveIntegerField(default=0, blank=True, null=True) 
    
    is_active = models.BooleanField(default=True, blank=True, null=True, help_text="Is the product visible to customers?") 
    is_featured = models.BooleanField(default=False, blank=True, null=True, help_text="Should this product be highlighted?") 
    
    seo_title = models.CharField(max_length=255, blank=True, null=True, help_text="SEO Title for search engines (max 60-70 chars).") 
    meta_description = models.TextField(blank=True, null=True, help_text="Meta Description for search engines (max 150-160 chars).") 

    created_at = models.DateTimeField(auto_now_add=True, null=True) 
    updated_at = models.DateTimeField(auto_now=True, null=True) 

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.slug == '':
            self.slug = None

        if self.name and not self.slug: 
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        if self.regular_price is not None and self.regular_price < 0:
            self.regular_price = 0
        if self.sale_price is not None and self.sale_price < 0:
            self.sale_price = 0

        super().save(*args, **kwargs)

    def get_display_price(self):
        if self.sale_price is not None:
            return self.sale_price
        elif self.regular_price is not None:
            return self.regular_price
        return None

    def __str__(self):
        return self.name or f"Product (ID: {self.id})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name='images', blank=True, null=True)
    image = models.ImageField(upload_to='product_images/%Y/%m/', blank=True, null=True) 
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True, # Reverted to null=True to avoid migration issues with existing data
        help_text="A unique name for this image within the product (e.g., 'front_view', 'detail_shot')."
    )
    alt_text = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Alt text for accessibility and SEO."
    )
    is_featured = models.BooleanField(
        default=False, 
        blank=True, 
        null=True, 
        help_text="Mark as the main image for the product."
    )
    order = models.PositiveIntegerField(
        default=0, 
        blank=True, 
        null=True, 
        help_text="Order in which images should appear."
    )

    class Meta:
        unique_together = ('product', 'name') 
        ordering = ['order', '-is_featured'] 

    def save(self, *args, **kwargs):
        if self.name == '':
            self.name = None

        if not self.name and self.image: 
            base_name = os.path.splitext(os.path.basename(self.image.name))[0] if self.image.name else "image"
            unique_name = base_name
            counter = 1
            if self.product:
                while ProductImage.objects.filter(product=self.product, name=unique_name).exclude(pk=self.pk).exists():
                    unique_name = f"{base_name}-{counter}"
                    counter += 1
            self.name = unique_name
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name if self.product else 'No Product'} - {self.name or self.image.name.split('/')[-1] if self.image else 'No Name'}"


class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variations", blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.size or ''} {self.weight or ''} {self.color or ''}".strip()
    

class DeliveryCharge(models.Model):
    zone = models.CharField(max_length=255, unique=True)  # Delivery Zone Name
    charge = models.DecimalField(max_digits=10, decimal_places=2)  # Delivery Charge Amount

    def __str__(self):
        return f"{self.zone} - {self.charge}"