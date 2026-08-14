import os
from uuid import uuid4

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

from datetime import datetime, timedelta, timezone

import jwt

load_dotenv()  # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing from .env.")



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


class LoginRequest(BaseModel):
    """The data users sends when logging in."""

    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """The JWT returned after successful login."""

    access_token: str
    token_type: str = "bearer"

def create_access_token(user_id: str, email: str) -> str:
    """
    Create a signed JWT that expires after the configured number of minutes.

    `sub` means subject, which identifies the logged-in user.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    token_payload = {
        "sub": user_id,
        "email": email,
        "exp": expires_at,
    }

    return jwt.encode(
        token_payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


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