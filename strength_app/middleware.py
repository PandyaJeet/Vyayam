class PermissionsPolicyMiddleware:
    """Security response headers (R2-W5).

    - Permissions-Policy: camera/mic restricted to self (the execute page
      needs the camera).
    - Referrer-Policy: same-origin — never leak patient URLs off-site.
    - Content-Security-Policy-Report-Only: ENFORCING a CSP today would
      break the app (inline scripts throughout + MediaPipe/Tailwind/font
      CDNs). Report-Only documents the target policy and surfaces
      violations in the browser console without breaking anything. Path to
      enforcement: move inline JS to static files (started with
      cv_core.js), add nonces, then flip to Content-Security-Policy.
    """

    CSP_REPORT_ONLY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://cdn.jsdelivr.net; "
        "media-src 'self' blob:; "
        "worker-src 'self' blob:"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(self), microphone=(self)'
        response['Referrer-Policy'] = 'same-origin'
        response.setdefault('Content-Security-Policy-Report-Only', self.CSP_REPORT_ONLY)
        return response
