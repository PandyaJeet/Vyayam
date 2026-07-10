"""
VYAYAM STRENGTH TRAINING - PROJECT URLS
Main URL configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from strength_app.rate_limiter import rate_limit

# D1 (2026-07 exam): every app login is limited 5/300s; the superuser login
# was the only unthrottled one. Same limiter, same budget. POST-only —
# rendering the admin login form is unaffected.
admin.site.login = rate_limit(
    max_attempts=5, window_seconds=300, key_prefix='admin_login',
)(admin.site.login)

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
