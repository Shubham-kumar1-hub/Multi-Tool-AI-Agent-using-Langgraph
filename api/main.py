import os
from uuid import uuid4

import psycopg
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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

class CreateThreadRequest(BaseModel):
    """Optional title supplied when a chat thread is created."""

    title: str | None = Field(
        default=None,
        max_length=120,
    )

class ThreadResponse(BaseModel):
    """Safe thread information returned to the frontend."""

    thread_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

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

# Reads the Authorization: Bearer <token> header.
# auto_error=False lets us return a clear 401 response ourselves.
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Verify the JWT and return the active user from PostgreSQL.

    Every future protected API route will use this function.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is  required.",
        )

    try:
        # Verify the JWT signature and expiration.
        token_payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = token_payload.get("sub")

        if not user_id:
            raise ValueError("JWT is missing the user ID")

    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    # verifying that the user still exists and is active in the database.
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """ 
                SELECT id, email, is_active
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            user = cursor.fetchone()

    if user is None or not user[2]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or does not exist.",
        )

    return {
        "id": str(user[0]),
        "email": user[1],
    }


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

@app.post("/auth/login", response_model=TokenResponse)
def login_user(payload: LoginRequest):
    """
    Authenticate a user and return a JWT for future requests.

    The JWT is signed with a secret key and expires after a configured number of minutes.
    """

    email = payload.email.lower().strip()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password_hash, is_active
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            user = cursor.fetchone()


    # This prevents attackers from discovering registered email addresses.
    if user is None or not password_hasher.verify(
        payload.password,
        user[1],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_id, _, is_active = user

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    access_token = create_access_token(
        user_id=str(user_id),
        email=email,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns the current user only when a valid Bearer JWT is supplied.
    """

    return {
        "message": "JWT verification succeeded.",
        "user": current_user,
    }

@app.post(
    "/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED
)
def create_thread(
    payload: CreateThreadRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new chat thread for the logged-in user.

    The returned thread_id will later be passed unchanged to LangGraph
    """

    thread_id = uuid4()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_threads (thread_id, user_id, title)
                VALUES (%s, %s, %s)
                RETURNING thread_id, title, created_at, updated_at
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

@app.get("/threads", response_model=list[ThreadResponse])
def list_my_threads(
    current_user: dict = Depends(get_current_user),
):
    """
    Return only threads owned by the authenticated user.

    This is the core authorization rule that prevents users from
    seeing each other's conversations.
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT thread_id, title, created_at, updated_at
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
   