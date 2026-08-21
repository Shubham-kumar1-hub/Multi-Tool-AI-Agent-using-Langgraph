# setup_auth_security_tables.py
# One-time migration for refresh tokens and global logout support.

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env.")

sql_statements = [
    # token_version lets "logout from all devices" invalidate all access JWTs.
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
    """,

    # Refresh tokens are stored as hashes, never as raw token values.
    """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT UNIQUE NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,

    # Makes refresh-token lookups fast.
    """
    CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens (user_id);
    """,
]

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cursor:
        for statement in sql_statements:
            cursor.execute(statement)

    conn.commit()

print("Authentication security tables are ready.")