from django.db import models


class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banners/')
    button_text = models.CharField(max_length=50, blank=True)
    button_link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    for_mobile = models.BooleanField(default=False)  # ✅ New field

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    image = models.ImageField(upload_to='testimonials/')
    is_active = models.BooleanField(default=True)
    for_mobile = models.BooleanField(default=False)  # ✅ show only on mobile if checked
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Testimonial #{self.id}"


class HomeComponents(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='home_components/')
    category = models.ForeignKey(
        'products.Category',
        on_delete=models.CASCADE,
        related_name='home_components'
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Homepage Component"
        verbose_name_plural = "Homepage Components"
