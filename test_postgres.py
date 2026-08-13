# test_postgres.py
# This file only verifies that Python can connect to PostgreSQL.

import os

import psycopg
from dotenv import load_dotenv

# Loads DATABASE_URL from the .env file in this folder.
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from your .env file.")

# Open a short-lived connection just for this test.
with psycopg.connect(database_url) as conn:
    with conn.cursor() as cursor:
        # Verify the database connection and server version.
        cursor.execute("SELECT current_database(), version();")
        database_name, postgres_version = cursor.fetchone()

        # Verify that the pgvector extension is available.
        cursor.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
        )
        vector_version = cursor.fetchone()[0]

print(f"Connected to database: {database_name}")
print(f"pgvector version: {vector_version}")
print(f"PostgreSQL: {postgres_version}")