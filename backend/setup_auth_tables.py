# setup_auth_tables.py
# One-time setup for authentication-related PostgreSQL tables.

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from the .env file.")

create_users_table = """
CREATE TABLE IF NOT EXISTS users (
    -- UUID is safer than exposing sequential user IDs.
    id UUID PRIMARY KEY,

    -- Email is unique, so one email can create only one account.
    email TEXT UNIQUE NOT NULL,

    -- Never store a plain-text password.
    -- We will store an Argon2 password hash here.
    password_hash TEXT NOT NULL,

    -- Lets us disable an accoount without deleting its data.
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- PostgreSQL automatically records when the account was created.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


with psycopg.connect(database_url) as conn:
    with conn.cursor() as cursor:
        cursor.execute(create_users_table)

    # Commits the table creation to the PostgreSQL database.
    conn.commit()

print("Authentication tables 'users' is ready.")
