"""Simple IP-based rate limiter using Django's cache framework."""
import os

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from functools import wraps


def rate_limit(max_attempts=5, window_seconds=300, key_prefix='rl'):
    """
    Decorator that limits requests per IP address.
    Default: 5 attempts per 5 minutes.
    Returns 429 Too Many Requests if exceeded.
    Only applies to POST requests; GET passes through freely.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            ip = _get_client_ip(request)
            cache_key = f'{key_prefix}:{ip}'

            attempts = cache.get(cache_key, 0)

            if attempts >= max_attempts:
                if request.headers.get('Accept', '').startswith('application/json'):
                    return JsonResponse(
                        {'error': 'Too many attempts. Please try again later.'},
                        status=429
                    )
                return HttpResponse(
                    '<h3>Too many attempts</h3>'
                    '<p>Please wait a few minutes before trying again.</p>'
                    '<p><a href="/">Go to homepage</a></p>',
                    status=429,
                    content_type='text/html'
                )

            cache.set(cache_key, attempts + 1, window_seconds)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _get_client_ip(request):
    """Get the client IP.

    DA-P6: X-Forwarded-For is client-controlled and trivially spoofed —
    honouring it unconditionally let anyone bypass the limiter with a
    random header per request. It is now trusted ONLY when the
    deployment explicitly declares a trusted proxy via
    DJANGO_TRUSTED_PROXY=1; otherwise REMOTE_ADDR is authoritative.
    """
    if os.environ.get('DJANGO_TRUSTED_PROXY') == '1':
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')
