# api/main.py
# Complete core JWT authentication API.
#
# This file does NOT change your Streamlit app or LangGraph agent logic.
# It provides authentication and ownership APIs that the UI will use next.

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

# Load values from .env.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env.")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing from .env.")

# Argon2 securely hashes user passwords.
password_hasher = PasswordHash.recommended()

# Reads Authorization: Bearer <JWT>.
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Multi-Tool Agent API",
    version="1.0.0",
)

# Allows your future Streamlit frontend to call FastAPI locally.
# Add your real HTTPS domain here when deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Request / response models
# -------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CreateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class ThreadResponse(BaseModel):
    thread_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


# -------------------------
# Token helper functions
# -------------------------

def hash_refresh_token(refresh_token: str) -> str:
    """
    Hash a refresh token before storing or searching for it.

    If the database is compromised, raw refresh tokens are not exposed.
    """

    return hashlib.sha256(
        refresh_token.encode("utf-8")
    ).hexdigest()


def create_access_token(
    user_id: str,
    email: str,
    token_version: int,
) -> str:
    """
    Create a short-lived JWT.

    token_version lets logout-all invalidate existing access tokens.
    """

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    token_payload = {
        "sub": user_id,
        "email": email,
        "token_type": "access",
        "token_version": token_version,
        "exp": expires_at,
    }

    return jwt.encode(
        token_payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_and_store_refresh_token(cursor, user_id: str) -> str:
    """
    Create a long-lived refresh token and store only its SHA-256 hash.
    """

    raw_refresh_token = secrets.token_urlsafe(48)
    refresh_token_hash = hash_refresh_token(raw_refresh_token)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    cursor.execute(
        """
        INSERT INTO refresh_tokens (
            id,
            user_id,
            token_hash,
            expires_at
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            uuid4(),
            user_id,
            refresh_token_hash,
            expires_at,
        ),
    )

    return raw_refresh_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Validate access JWT, then verify the user still exists and is active.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required.",
        )

    try:
        token_payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = token_payload.get("sub")
        token_type = token_payload.get("token_type")
        token_version = token_payload.get("token_version")

        if not user_id or token_type != "access":
            raise ValueError("Invalid access token.")

    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, email, is_active, token_version
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            user = cursor.fetchone()

    # Reject deleted, disabled, or globally logged-out accounts.
    if (
        user is None
        or not user[2]
        or user[3] != token_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    return {
        "id": str(user[0]),
        "email": user[1],
    }


# -------------------------
# Basic health route
# -------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "API is running",
    }


# -------------------------
# Authentication routes
# -------------------------

@app.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
)
def register_user(payload: RegisterRequest):
    """
    Create a user. Passwords are stored only as Argon2 hashes.
    """

    email = payload.email.lower().strip()
    user_id = uuid4()
    password_hash = password_hasher.hash(payload.password)

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (
                        id,
                        email,
                        password_hash
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        email,
                        password_hash,
                    ),
                )

            conn.commit()

    except UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return {
        "message": "Account created successfully.",
        "user": {
            "id": str(user_id),
            "email": email,
        },
    }


@app.post(
    "/auth/login",
    response_model=TokenResponse,
)
def login_user(payload: LoginRequest):
    """
    Verify credentials and issue:
    - Short-lived access JWT
    - Long-lived refresh token
    """

    email = payload.email.lower().strip()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password_hash, is_active, token_version
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            user = cursor.fetchone()

            # Same error for an unknown email and wrong password.
            if user is None or not password_hasher.verify(
                payload.password,
                user[1],
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password.",
                )

            user_id, _, is_active, token_version = user

            if not is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This account is disabled.",
                )

            refresh_token = create_and_store_refresh_token(
                cursor,
                str(user_id),
            )

        conn.commit()

    access_token = create_access_token(
        user_id=str(user_id),
        email=email,
        token_version=token_version,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post(
    "/auth/refresh",
    response_model=TokenResponse,
)
def refresh_access_token(payload: RefreshTokenRequest):
    """
    Replace a valid refresh token with a new access + refresh token pair.

    This is refresh-token rotation: the old refresh token becomes invalid.
    """

    refresh_token_hash = hash_refresh_token(payload.refresh_token)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    refresh_tokens.id,
                    refresh_tokens.user_id,
                    refresh_tokens.expires_at,
                    users.email,
                    users.is_active,
                    users.token_version
                FROM refresh_tokens
                JOIN users
                    ON users.id = refresh_tokens.user_id
                WHERE refresh_tokens.token_hash = %s
                    AND refresh_tokens.revoked_at IS NULL
                """,
                (refresh_token_hash,),
            )
            stored_token = cursor.fetchone()

            if (
                stored_token is None
                or stored_token[2] <= datetime.now(timezone.utc)
                or not stored_token[4]
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token.",
                )

            token_id, user_id, _, email, _, token_version = stored_token

            # Revoke the old token before creating a replacement.
            cursor.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW()
                WHERE id = %s
                """,
                (token_id,),
            )

            new_refresh_token = create_and_store_refresh_token(
                cursor,
                str(user_id),
            )

        conn.commit()

    new_access_token = create_access_token(
        user_id=str(user_id),
        email=email,
        token_version=token_version,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/logout")
def logout_user(
    payload: RefreshTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Log out one device/session by revoking its refresh token.

    The current access JWT stays valid only until its short expiry.
    """

    refresh_token_hash = hash_refresh_token(payload.refresh_token)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW()
                WHERE token_hash = %s
                    AND user_id = %s
                    AND revoked_at IS NULL
                """,
                (
                    refresh_token_hash,
                    current_user["id"],
                ),
            )

        conn.commit()

    return {
        "message": "Logged out successfully.",
    }


@app.post("/auth/logout-all")
def logout_from_all_devices(
    current_user: dict = Depends(get_current_user),
):
    """
    Revoke every refresh token and invalidate every current access JWT.
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            # Invalidates all access JWTs through token_version mismatch.
            cursor.execute(
                """
                UPDATE users
                SET token_version = token_version + 1
                WHERE id = %s
                """,
                (current_user["id"],),
            )

            # Invalidates all refresh tokens.
            cursor.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW()
                WHERE user_id = %s
                    AND revoked_at IS NULL
                """,
                (current_user["id"],),
            )

        conn.commit()

    return {
        "message": "Logged out from all devices.",
    }


@app.get("/auth/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated user profile."""

    return {
        "message": "JWT verification succeeded.",
        "user": current_user,
    }


# -------------------------
# Protected thread routes
# -------------------------

@app.post(
    "/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_thread(
    payload: CreateThreadRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a LangGraph-compatible thread ID owned by the logged-in user.
    """

    thread_id = uuid4()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_threads (
                    thread_id,
                    user_id,
                    title
                )
                VALUES (%s, %s, %s)
                RETURNING
                    thread_id,
                    title,
                    created_at,
                    updated_at
                """,
                (
                    thread_id,
                    current_user["id"],
                    payload.title,
                ),
            )
            created_thread = cursor.fetchone()

        conn.commit()

    return {
        "thread_id": str(created_thread[0]),
        "title": created_thread[1],
        "created_at": created_thread[2],
        "updated_at": created_thread[3],
    }


@app.get(
    "/threads",
    response_model=list[ThreadResponse],
)
def list_my_threads(
    current_user: dict = Depends(get_current_user),
):
    """
    Return only threads owned by the authenticated user.
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    thread_id,
                    title,
                    created_at,
                    updated_at
                FROM app_threads
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (current_user["id"],),
            )
            threads = cursor.fetchall()

    return [
        {
            "thread_id": str(thread[0]),
            "title": thread[1],
            "created_at": thread[2],
            "updated_at": thread[3],
        }
        for thread in threads
    ]