"""
VYAYAM STRENGTH TRAINING - PROJECT URLS
Main URL configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('therapist/', include('therapist_app.urls')),
    path('', include('strength_app.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "VYAYAM Strength Training Admin"
admin.site.site_title = "VYAYAM Admin Portal"
admin.site.index_title = "Welcome to VYAYAM Administration"

# Custom error handlers
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
