"""Project-wide template context processors."""

from django.conf import settings


def sentry(request):
    """Expose the Sentry DSN to templates for the browser loader.

    Reads settings lazily (not module-level) so tests can flip it with
    override_settings. Empty string when SENTRY_DSN is unset — the loader
    include renders nothing in that case (dev/CI: zero behavior change).
    """
    return {'SENTRY_DSN': getattr(settings, 'SENTRY_DSN', '')}
