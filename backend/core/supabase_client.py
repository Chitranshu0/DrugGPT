"""Supabase client setup and authentication helpers.

Two clients are used:

* the **publishable** client for sign-in, sign-up, token refresh, and token
  verification (the same privileges a browser has);
* the **secret** client for admin work such as bootstrapping the first user.
  It is optional and must never leave the backend.

Nothing connects at import time. Clients are created lazily and cached.
"""

import logging
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from backend.core.config import (
    SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_SECRET_KEY,
    SUPABASE_URL,
)

logger = logging.getLogger(__name__)

# Values copied from .env.example are not real keys. Treating them as absent
# gives a clear "not configured" path instead of failing on every API call.
_PLACEHOLDER_PREFIXES = ("paste_your", "your_", "replace_me", "changeme")


def _usable_key(value: str) -> bool:
    cleaned = (value or "").strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    return not lowered.startswith(_PLACEHOLDER_PREFIXES)


class AuthConfigError(RuntimeError):
    """Raised when Supabase settings are missing from the environment."""


class AuthError(RuntimeError):
    """A user-facing authentication failure.

    The message is safe to return to the client. It never includes tokens,
    passwords, or raw Supabase error payloads.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@lru_cache
def get_auth_client() -> Client:
    """Return the shared publishable Supabase client."""
    if not SUPABASE_URL or not _usable_key(SUPABASE_PUBLISHABLE_KEY):
        raise AuthConfigError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set in .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


@lru_cache
def get_admin_client() -> Client | None:
    """Return the admin client, or None when no usable secret key is set."""
    if not SUPABASE_URL or not _usable_key(SUPABASE_SECRET_KEY):
        return None
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def user_payload(user: Any) -> dict[str, str]:
    """Reduce a Supabase user object to the fields the app needs."""
    return {
        "id": str(user.id),
        "email": user.email or "",
    }


def _session_payload(session: Any, user: Any) -> dict[str, Any]:
    """Build the token payload returned by the auth routes."""
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
        "expires_in": session.expires_in,
        "token_type": session.token_type or "bearer",
        "user": user_payload(user),
    }


def verify_token(token: str) -> dict[str, str] | None:
    """Return the user for a valid access token, or None when invalid.

    Supabase validates the signature and expiry; the backend never decodes or
    trusts the JWT on its own.
    """
    if not token:
        return None

    try:
        response = get_auth_client().auth.get_user(token)
    except AuthConfigError:
        raise
    except Exception:
        logger.info("Rejected an invalid or expired Supabase access token")
        return None

    if not response or not response.user:
        return None

    return user_payload(response.user)


def sign_in(email: str, password: str) -> dict[str, Any]:
    """Sign a user in and return their tokens plus profile."""
    try:
        response = get_auth_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except AuthConfigError:
        raise
    except Exception as exc:
        raise AuthError("Invalid email or password", 401) from exc

    if not response or not response.session or not response.user:
        raise AuthError("Invalid email or password", 401)

    return _session_payload(response.session, response.user)


def sign_up(email: str, password: str) -> dict[str, Any]:
    """Create a user and sign them in.

    When a secret key is configured, the account is auto-confirmed through the
    admin API so the user can start chatting immediately. Without a secret key
    Supabase's own email-confirmation setting applies, and the response asks
    the user to confirm their address.
    """
    admin = get_admin_client()

    if admin is not None:
        try:
            admin.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                }
            )
        except Exception:
            # The user may already exist; signing in below is the real check.
            pass

        return sign_in(email, password)

    try:
        response = get_auth_client().auth.sign_up(
            {"email": email, "password": password}
        )
    except AuthConfigError:
        raise
    except Exception as exc:
        raise AuthError("Could not create the account", 400) from exc

    if not response:
        raise AuthError("Could not create the account", 400)

    if response.session:
        return _session_payload(response.session, response.user)

    return {
        "requires_confirmation": True,
        "user": user_payload(response.user),
    }


def refresh_session(refresh_token: str) -> dict[str, Any]:
    """Exchange a refresh token for a new access token."""
    try:
        response = get_auth_client().auth.refresh_session(refresh_token)
    except AuthConfigError:
        raise
    except Exception as exc:
        raise AuthError("Session expired, please sign in again", 401) from exc

    if not response or not response.session or not response.user:
        raise AuthError("Session expired, please sign in again", 401)

    return _session_payload(response.session, response.user)


def find_user_by_email(email: str) -> dict[str, str] | None:
    """Look up a user through the admin API (used by the bootstrap step)."""
    admin = get_admin_client()
    if admin is None:
        return None

    target = email.strip().lower()
    try:
        users = admin.auth.admin.list_users()
    except Exception:
        logger.warning("Could not list Supabase users for the bootstrap step")
        return None

    for user in users or []:
        if (user.email or "").strip().lower() == target:
            return user_payload(user)

    return None


def create_confirmed_user(email: str, password: str) -> dict[str, str] | None:
    """Create an already-confirmed user via the admin API."""
    admin = get_admin_client()
    if admin is None:
        return None

    try:
        response = admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    except Exception:
        return None

    if not response or not response.user:
        return None

    return user_payload(response.user)
