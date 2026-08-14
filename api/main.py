import os
from uuid import uuid4

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

load_dotenv()  # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")


# Argon2 hashes passwords securely; passwords are never stored directly.
password_hasher = PasswordHash.recommended()

# creates the fastapi appliaction.
app = FastAPI(
    title="Multi-Tool Agent API",
    version="1.0.0",
)

class RegisterRequest(BaseModel):
    """The data users sends when registering a new account."""

    email: EmailStr = Field(..., description="The user's email address.")

    password: str = Field(min_length=8, max_length=128, description="The user's password.")


@app.get("/health")
def health_check():
    """
    A simple endpoint to confirm that the API is running.
    """

    return {
        "status": "ok",
        "message": "Api is running successfully.",
    }

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest):
    """
    Create a new user account.

    The database stores only the Argon2 hash, never the plain password.
    """

    # Normalizing prevents separate accounts such as A@Email.com and a@email.com.
    email = payload.email.lower().strip()

    # generates a random UUID for the new user.
    user_id = uuid4()

    # Securely hashing the supplied password before saving it.
    password_hash = password_hasher.hash(payload.password)

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # %s parameters protect against SQL injection.
                cursor.execute(
                    """
                    INSERT INTO users (id, email, password_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, email, password_hash),
                )

            conn.commit()

    except UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return {
        "message": "Account has been created successfully.",
        "user": {
            "id": str(user_id),
            "email": email,
        },
    }