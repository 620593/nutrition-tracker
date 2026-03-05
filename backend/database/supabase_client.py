"""
This file creates and returns configured Supabase client instances for the backend.
It reads connection credentials from environment variables (loaded via python-dotenv)
and uses the official supabase-py library to establish the connection.

Two clients are exposed:
  - get_supabase_client()  → service-role client for privileged server-side operations
  - get_anon_client()      → anon-key client that respects Row Level Security policies,
                             intended for user-facing requests that mirror what the
                             frontend would be allowed to do.

Supabase project reference: hyejucwqghkujckoshbr
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file: database/ → backend/ → root)
_dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_dotenv_path)


def get_supabase_client() -> Client:
    """
    Returns a Supabase client authenticated with the SERVICE_ROLE key.
    This client bypasses Row Level Security and must only be used for
    trusted, server-side operations (e.g. writing nutrition logs, upserting
    daily goals, querying aggregate data for the leaderboard).

    Environment variables required:
        SUPABASE_URL         – e.g. https://hyejucwqghkujckoshbr.supabase.co
        SUPABASE_SERVICE_KEY – service_role JWT (keep this secret, never expose to clients)

    Raises:
        ValueError: if either environment variable is missing or empty.
    """
    url: str = os.environ.get("SUPABASE_URL", "").strip()
    service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url:
        raise ValueError(
            "SUPABASE_URL is not set. "
            "Add it to your .env file: SUPABASE_URL=https://<project>.supabase.co"
        )
    if not service_key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Add it to your .env file: SUPABASE_SERVICE_ROLE_KEY=<service_role_jwt>"
        )

    return create_client(url, service_key)


def get_anon_client() -> Client:
    """
    Returns a Supabase client authenticated with the ANON (public) key.
    This client honours Row Level Security policies and is appropriate for
    any operation that should be scoped to data the authenticated user is
    allowed to see (e.g. reading the current user's own meals or goals).

    Environment variables required:
        SUPABASE_URL      – e.g. https://hyejucwqghkujckoshbr.supabase.co
        SUPABASE_ANON_KEY – anon/public JWT (safe to expose to the browser)

    Raises:
        ValueError: if either environment variable is missing or empty.
    """
    url: str = os.environ.get("SUPABASE_URL", "").strip()
    anon_key: str = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not url:
        raise ValueError(
            "SUPABASE_URL is not set. "
            "Add it to your .env file: SUPABASE_URL=https://<project>.supabase.co"
        )
    if not anon_key:
        raise ValueError(
            "SUPABASE_ANON_KEY is not set. "
            "Add it to your .env file: SUPABASE_ANON_KEY=<anon_jwt>"
        )

    return create_client(url, anon_key)


__all__ = ["get_supabase_client", "get_anon_client"]
