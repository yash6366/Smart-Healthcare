from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """CORE Domain admin for VakCare platform user accounts."""

    list_display = (
        "username",
        "email",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_verified", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "VakCare Profile",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "is_verified",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "VakCare Profile",
            {
                "fields": ("email", "role", "phone_number", "is_verified"),
            },
        ),
    )

