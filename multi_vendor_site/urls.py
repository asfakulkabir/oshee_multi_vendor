from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns # new
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),#new
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),#new
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('accounts/', include('accounts.urls')),  #Include the website app URLs
    path('dashboard/', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)