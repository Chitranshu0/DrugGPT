"""First-run bootstrap for the multi-user setup.

When ``BOOTSTRAP_ADMIN_EMAIL`` and ``BOOTSTRAP_ADMIN_PASSWORD`` are set, the
application makes sure that account exists in Supabase, marks it as the local
admin, and hands any pre-multi-user conversations to it.

This runs once per startup and never raises: a Supabase outage should not stop
the API from booting.
"""

import logging

from backend.core.config import BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD
from backend.core.supabase_client import (
    create_confirmed_user,
    find_user_by_email,
    get_admin_client,
)
from backend.memory import conversations, users

logger = logging.getLogger(__name__)


async def bootstrap_admin() -> None:
    """Create/confirm the bootstrap admin and backfill unowned threads."""
    if not BOOTSTRAP_ADMIN_EMAIL or not BOOTSTRAP_ADMIN_PASSWORD:
        logger.info("BOOTSTRAP_ADMIN_EMAIL/PASSWORD not set; skipping bootstrap")
        return

    if get_admin_client() is None:
        logger.warning(
            "Bootstrap admin is configured but SUPABASE_SECRET_KEY is missing; "
            "skipping bootstrap"
        )
        return

    profile = find_user_by_email(BOOTSTRAP_ADMIN_EMAIL)
    if profile is None:
        profile = create_confirmed_user(
            BOOTSTRAP_ADMIN_EMAIL,
            BOOTSTRAP_ADMIN_PASSWORD,
        )

    if profile is None:
        logger.warning("Could not create or find the bootstrap admin user")
        return

    await users.upsert_user(profile["id"], profile["email"], is_admin=True)
    assigned = await conversations.assign_unowned_threads(profile["id"])

    logger.info(
        "Bootstrap admin %s ready (%d unowned conversation(s) assigned)",
        profile["email"],
        assigned,
    )
