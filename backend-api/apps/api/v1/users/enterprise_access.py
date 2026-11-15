"""Tenant-safe checks for verified company accounts (no Django superuser bypass)."""


def enterprise_access(user):
    """Return (enterprise, is_owner), or (None, False) for unauthorized users."""
    if (
        not user or not user.is_authenticated or not user.is_active
        or user.is_banned or user.role != "enterprise"
    ):
        return None, False
    owner = getattr(user, "enterprise_profile", None)
    if owner is not None:
        if owner.is_active and owner.verified_at is not None:
            return owner, True
        return None, False
    membership = getattr(user, "enterprise_membership", None)
    if membership is None or not membership.is_active:
        return None, False
    company = membership.enterprise
    if not company.is_active or company.verified_at is None:
        return None, False
    if not company.user.is_active or company.user.is_banned:
        return None, False
    return company, False
