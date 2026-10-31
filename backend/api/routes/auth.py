"""Authentication routes backed by Supabase Auth.

The frontend never talks to Supabase directly. It sends credentials here and
receives an access token plus a refresh token; every other route expects that
access token as ``Authorization: Bearer <token>``.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_current_user
from backend.api.schemas import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthSession,
    AuthSignupRequest,
    AuthSignupResponse,
    AuthUser,
)
from backend.core.supabase_client import (
    AuthConfigError,
    AuthError,
    refresh_session,
    sign_in,
    sign_up,
)
from backend.memory import users

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_http(exc: AuthError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


async def _sync_session(raw: dict) -> AuthSession:
    """Upsert the local user row and build the response model."""
    local = await users.upsert_user(raw["user"]["id"], raw["user"]["email"])
    return AuthSession(
        access_token=raw["access_token"],
        refresh_token=raw["refresh_token"],
        expires_at=raw.get("expires_at"),
        expires_in=raw.get("expires_in"),
        token_type=raw.get("token_type", "bearer"),
        user=AuthUser(
            id=local["user_id"],
            email=local["email"],
            is_admin=local["is_admin"],
        ),
    )


@router.post(
    "/signup",
    response_model=AuthSignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(payload: AuthSignupRequest) -> AuthSignupResponse:
    """Create an account and sign in, or ask the user to confirm their email."""
    try:
        raw = sign_up(payload.email.strip(), payload.password)
    except AuthError as exc:
        _raise_http(exc)
    except AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if raw.get("requires_confirmation"):
        return AuthSignupResponse(
            requires_confirmation=True,
            user=AuthUser(**raw["user"]),
            session=None,
        )

    return AuthSignupResponse(
        requires_confirmation=False,
        user=AuthUser(**raw["user"]),
        session=await _sync_session(raw),
    )


@router.post("/login", response_model=AuthSession)
async def login(payload: AuthLoginRequest) -> AuthSession:
    """Sign in with email and password."""
    try:
        raw = sign_in(payload.email.strip(), payload.password)
    except AuthError as exc:
        _raise_http(exc)
    except AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return await _sync_session(raw)


@router.post("/refresh", response_model=AuthSession)
async def refresh(payload: AuthRefreshRequest) -> AuthSession:
    """Exchange a refresh token for a new access token."""
    try:
        raw = refresh_session(payload.refresh_token)
    except AuthError as exc:
        _raise_http(exc)
    except AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return await _sync_session(raw)


@router.get("/me", response_model=AuthUser)
async def me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Return the signed-in account."""
    return user
