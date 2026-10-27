import logging
from typing import Any
from django.http import HttpRequest
from .models import AuditLog

logger = logging.getLogger("apps.audit")

SENSITIVE_KEYS = {
    "password",
    "password_confirm",
    "new_password",
    "old_password",
    "token",
    "access",
    "refresh",
    "secret",
    "api_key",
    "authorization",
}


def sanitize_details(details: dict[str, Any] | None) -> dict[str, Any]:
    """
    Recursively strips passwords, tokens, and sensitive security details from audit payloads.
    """
    if not details or not isinstance(details, dict):
        return {}

    sanitized = {}
    for key, value in details.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_details(value)
        else:
            sanitized[key] = value
    return sanitized


def get_client_ip(request: HttpRequest | None) -> str | None:
    """Extract client IP address from request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    event_type: str,
    actor=None,
    resource_type: str = "",
    resource_id: str = "",
    action: str = "",
    details: dict[str, Any] | None = None,
    is_success: bool = True,
    request: HttpRequest | None = None,
) -> AuditLog | None:
    """
    Securely writes an immutable audit record.
    Never fails the calling request if audit recording encounters an error.
    """
    try:
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""
        cleaned_details = sanitize_details(details)

        # If actor was not explicitly passed, inspect request
        if actor is None and request and hasattr(request, "user") and request.user.is_authenticated:
            actor = request.user

        return AuditLog.objects.create(
            event_type=event_type,
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=str(resource_id),
            action=action,
            details=cleaned_details,
            is_success=is_success,
        )
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)
        return None
