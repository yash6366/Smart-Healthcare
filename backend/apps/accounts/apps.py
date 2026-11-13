from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """CORE Domain: Identity, roles, and authentication (table: accounts_user)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
