"""Create a DrugGPT user (and optionally adopt existing chats).

Run from the project root:

    python -m scripts.create_user you@example.com --admin
    python -m scripts.create_user you@example.com --password secret123 --claim-unowned

Requires a real ``SUPABASE_SECRET_KEY`` because it uses the Supabase admin API.
If the account already exists, only the local row is refreshed.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from backend.core.config import BOOTSTRAP_ADMIN_EMAIL
from backend.core.supabase_client import (
    create_confirmed_user,
    find_user_by_email,
    get_admin_client,
)
from backend.memory import conversations, users
from backend.memory.db import init_app_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a confirmed Supabase user for DrugGPT.",
    )
    parser.add_argument("email", help="Email address for the account")
    parser.add_argument(
        "--password",
        default=None,
        help="Password (prompted when the account does not exist yet)",
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Mark the local account as an admin",
    )
    parser.add_argument(
        "--claim-unowned",
        action="store_true",
        help="Assign conversations that have no owner to this account",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    if get_admin_client() is None:
        print(
            "Set a real SUPABASE_SECRET_KEY in .env first "
            "(the admin API is required to create users).",
            file=sys.stderr,
        )
        return 1

    await init_app_db()

    email = args.email.strip()
    profile = find_user_by_email(email)

    if profile is None:
        password = args.password or getpass.getpass("Password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters.", file=sys.stderr)
            return 1
        profile = create_confirmed_user(email, password)

    if profile is None:
        print(
            f"Could not create {email}. Check the Supabase logs and that the "
            "email is not already registered.",
            file=sys.stderr,
        )
        return 1

    local = await users.upsert_user(
        profile["id"],
        profile["email"],
        is_admin=True if args.admin else None,
    )

    print(f"User ready: {local['email']} (admin={local['is_admin']})")

    if args.claim_unowned:
        assigned = await conversations.assign_unowned_threads(profile["id"])
        print(f"Assigned {assigned} ownerless conversation(s).")

    if not BOOTSTRAP_ADMIN_EMAIL:
        print(
            "Tip: set BOOTSTRAP_ADMIN_EMAIL/PASSWORD to do this automatically "
            "on startup."
        )

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
