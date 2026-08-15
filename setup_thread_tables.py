# setup_thread_tables.py
# Creates application-owned thread metadata.
#
# This is separate from LangGraph's internal checkpoint tables.
# LangGraph still stores graph state using the same thread_id.

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env.")

create_threads_table = """
CREATE TABLE IF NOT EXISTS app_threads (
    -- This is the same UUID used as LangGraph's thread_id.
    thread_id UUID PRIMARY KEY,

    -- Each chat belongs to exactly one authenticated user.
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- We will save generated chat titles here later.
    title TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

create_user_thread_index = """
CREATE INDEX IF NOT EXISTS idx_app_threads_user_id
ON app_threads (user_id);
"""

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cursor:
        cursor.execute(create_threads_table)
        cursor.execute(create_user_thread_index)

    conn.commit()

print("Thread ownership table 'app_threads' is ready.")