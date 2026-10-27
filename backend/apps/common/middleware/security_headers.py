"""
Security Headers & Content-Security-Policy Middleware for VakCare.
Enforces defense-in-depth HTTP security response headers across all API and document endpoints.
"""
from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Attaches defense-in-depth security headers to all HTTP responses:
    - Content-Security-Policy (CSP)
    - Permissions-Policy
    - Referrer-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1. Content-Security-Policy
        # Configurable connect-src to support diverse development and production hosts
        default_connect = (
            "'self' http://127.0.0.1:8000 http://localhost:8000 "
            "http://127.0.0.1:8080 http://localhost:8080 "
            "ws://127.0.0.1:8000 ws://localhost:8000"
        )
        connect_src = getattr(settings, "CSP_CONNECT_SRC", default_connect)

        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: https:",
            f"connect-src {connect_src}",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # 2. Permissions-Policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # 3. Referrer-Policy
        if "Referrer-Policy" not in response.headers:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 4. X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 5. X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        return response
