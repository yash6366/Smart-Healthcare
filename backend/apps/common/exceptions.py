import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("apps.common")


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler returning unified JSON error envelopes:
    {
        "status": "error",
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable summary",
            "details": {...} or [...]
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        code = "API_ERROR"
        status_code = response.status_code

        if status_code == status.HTTP_400_BAD_REQUEST:
            code = "VALIDATION_ERROR"
        elif status_code == status.HTTP_401_UNAUTHORIZED:
            code = "AUTHENTICATION_FAILED"
        elif status_code == status.HTTP_403_FORBIDDEN:
            code = "PERMISSION_DENIED"
            try:
                from apps.audit.services import log_audit_event
                req = context.get("request") if context else None
                user = getattr(req, "user", None) if req else None
                view_cls = context.get("view").__class__.__name__ if (context and "view" in context) else "View"
                log_audit_event(
                    event_type="PERMISSION_DENIED",
                    actor=user if (user and getattr(user, "is_authenticated", False)) else None,
                    resource_type=view_cls,
                    resource_id="",
                    action=f"FORBIDDEN_{getattr(req, 'method', 'REQUEST')}",
                    details={"path": getattr(req, "path", ""), "reason": str(exc)},
                    is_success=False,
                    request=req,
                )
            except Exception as audit_err:
                logger.debug("Failed to record permission failure audit log: %s", audit_err)
        elif status_code == status.HTTP_404_NOT_FOUND:
            code = "RESOURCE_NOT_FOUND"
        elif status_code == status.HTTP_409_CONFLICT:
            code = "CONFLICT"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            code = "RATE_LIMIT_EXCEEDED"

        # Extract message and details
        data = response.data
        message = "An error occurred while processing the request."
        details = data

        if isinstance(data, dict):
            if "detail" in data:
                message = str(data["detail"])
                details = None
            elif "non_field_errors" in data:
                message = " ".join([str(err) for err in data["non_field_errors"]])
        elif isinstance(data, list):
            message = " ".join([str(item) for item in data])
            details = None

        response.data = {
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        }
    else:
        # Unexpected server error
        logger.exception("Unhandled server exception: %s", exc)
        response = Response(
            {
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "details": None,
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
