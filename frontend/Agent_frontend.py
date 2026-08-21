# Agent_frontend.py
# Streamlit UI that talks only to protected FastAPI routes.


import json
import os

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
)


# ----------------------
# Authentication helpers
# ----------------------

def clear_authentication():
    """Removing tokens and all user-specific UI state."""

    for key in [
        "access_token",
        "refresh_token",
        "current_user",
        "thread_id",
        "message_history",
        "awaiting_approval",
        "pending_interrupt_msg",
        "uploaded_files",
    ]:
        st.session_state.pop(key, None)


def refresh_access_token() -> bool:
    """
    Exchanging a valid refresh token for a new short-lived access token.
    """

    refresh_token = st.session_state.get("refresh_token")

    if not refresh_token:
        return False

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=20,
        )

        if response.status_code != 200:
            clear_authentication()
            return False

        tokens = response.json()

        st.session_state["access_token"] = tokens["access_token"]
        st.session_state["refresh_token"] = tokens["refresh_token"]

        return True

    except requests.RequestException:
        return False


def api_request(
    method: str,
    path: str,
    *,
    retry_after_refresh: bool = True,
    **kwargs,
) -> requests.Response:
    """
    Making an authenticated FastAPI request.

    If the 15-minute access token expired, refresh it once automatically.
    """

    access_token = st.session_state.get("access_token")

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"

    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        headers=headers,
        timeout=60,
        **kwargs,
    )

    if (
        response.status_code == 401
        and retry_after_refresh
        and refresh_access_token()
    ):
        headers["Authorization"] = (
            f"Bearer {st.session_state['access_token']}"
        )

        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            headers=headers,
            timeout=60,
            **kwargs,
        )

    return response


def show_authentication_page():
    """Display login and registration forms until the user authenticates."""

    st.title("Multi Utility Chatbot")
    st.caption("Sign in to access your private chats and PDFs.")

    login_tab, register_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            login_clicked = st.form_submit_button("Login")

        if login_clicked:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/auth/login",
                    json={
                        "email": email,
                        "password": password,
                    },
                    timeout=20,
                )

                if response.status_code != 200:
                    st.error(
                        response.json().get(
                            "detail",
                            "Login failed.",
                        )
                    )
                else:
                    tokens = response.json()

                    st.session_state["access_token"] = (
                        tokens["access_token"]
                    )
                    st.session_state["refresh_token"] = (
                        tokens["refresh_token"]
                    )

                    profile_response = api_request("GET", "/auth/me")

                    if profile_response.status_code == 200:
                        st.session_state["current_user"] = (
                            profile_response.json()["user"]
                        )
                        st.rerun()
                    else:
                        st.error("Could not load your profile.")

            except requests.RequestException:
                st.error(
                    "Cannot connect to FastAPI. "
                    "Make sure uvicorn is running."
                )

    with register_tab:
        with st.form("register_form"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input(
                "Password",
                type="password",
                key="register_password",
            )
            register_clicked = st.form_submit_button("Create account")

        if register_clicked:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/auth/register",
                    json={
                        "email": email,
                        "password": password,
                    },
                    timeout=20,
                )

                if response.status_code == 201:
                    st.success(
                        "Account created. You can now log in."
                    )
                else:
                    st.error(
                        response.json().get(
                            "detail",
                            "Could not create account.",
                        )
                    )

            except requests.RequestException:
                st.error(
                    "Cannot connect to FastAPI. "
                    "Make sure uvicorn is running."
                )


# ----------------------
# Thread API helpers
# ----------------------

def get_threads() -> list[dict]:
    """Load only the authenticated user's threads."""

    response = api_request("GET", "/threads")

    if response.status_code == 200:
        return response.json()

    return []


def create_thread() -> str | None:
    """Create a JWT-owned thread ID through FastAPI."""

    response = api_request(
        "POST",
        "/threads",
        json={"title": None},
    )

    if response.status_code == 201:
        return response.json()["thread_id"]

    st.error("Could not create a new chat.")
    return None


def load_conversation(thread_id: str):
    """Load messages and approval state for an owned thread."""

    response = api_request(
        "GET",
        f"/threads/{thread_id}/messages",
    )

    if response.status_code != 200:
        st.error("Could not load this chat.")
        return

    conversation = response.json()

    st.session_state["message_history"] = (
        conversation["messages"]
    )
    st.session_state["awaiting_approval"] = bool(
        conversation["pending_interrupt"]
    )
    st.session_state["pending_interrupt_msg"] = (
        conversation["pending_interrupt"]
    )


def ensure_current_thread(threads: list[dict]):
    """Create a first chat or select a valid existing chat."""

    known_thread_ids = {
        thread["thread_id"]
        for thread in threads
    }

    current_thread = st.session_state.get("thread_id")

    if current_thread not in known_thread_ids:
        new_thread_id = create_thread()

        if new_thread_id:
            st.session_state["thread_id"] = new_thread_id
            st.session_state["message_history"] = []
            st.session_state["awaiting_approval"] = False
            st.session_state["pending_interrupt_msg"] = None
            st.session_state["uploaded_files"] = {}


def stream_agent_reply(thread_id: str, user_input: str):
    """
    Read FastAPI Server-Sent Events and yield only AI text to Streamlit.
    """

    url = f"{API_BASE_URL}/threads/{thread_id}/chat/stream"

    headers = {
        "Authorization": (
            f"Bearer {st.session_state['access_token']}"
        ),
    }

    response = requests.post(
        url,
        headers=headers,
        json={"message": user_input},
        stream=True,
        timeout=120,
    )

    # Retry one time if the access token expired.
    if response.status_code == 401 and refresh_access_token():
        headers["Authorization"] = (
            f"Bearer {st.session_state['access_token']}"
        )

        response = requests.post(
            url,
            headers=headers,
            json={"message": user_input},
            stream=True,
            timeout=120,
        )

    if response.status_code != 200:
        message = "Could not contact the agent."

        try:
            message = response.json().get("detail", message)
        except ValueError:
            pass

        st.error(message)
        return

    current_event = ""

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        if raw_line.startswith("event:"):
            current_event = raw_line.removeprefix(
                "event:"
            ).strip()
            continue

        if not raw_line.startswith("data:"):
            continue

        payload = json.loads(
            raw_line.removeprefix("data:").strip()
        )

        if current_event == "token":
            yield payload["text"]

        elif current_event == "tool":
            st.session_state["message_history"].append(
                {
                    "role": "tool",
                    "content": payload["content"],
                }
            )

        elif current_event == "interrupt":
            st.session_state["awaiting_approval"] = True
            st.session_state["pending_interrupt_msg"] = (
                payload["message"]
            )

        elif current_event == "error":
            st.error(payload["message"])


# ----------------------
# Session initialization
# ----------------------

if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = None

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "awaiting_approval" not in st.session_state:
    st.session_state["awaiting_approval"] = False

if "pending_interrupt_msg" not in st.session_state:
    st.session_state["pending_interrupt_msg"] = None

if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = {}

# Stop before rendering the chat if no user is authenticated.
if not st.session_state["access_token"]:
    show_authentication_page()
    st.stop()

# Verify the current token and load profile after a page refresh.
if "current_user" not in st.session_state:
    profile_response = api_request("GET", "/auth/me")

    if profile_response.status_code != 200:
        clear_authentication()
        st.rerun()

    st.session_state["current_user"] = (
        profile_response.json()["user"]
    )

# ----------------------
# Load private chat state
# ----------------------

threads = get_threads()
ensure_current_thread(threads)

thread_id = st.session_state.get("thread_id")

if not thread_id:
    st.error("Could not create a chat thread.")
    st.stop()

# Load messages only when entering a different thread or first loading.
if st.session_state.get("loaded_thread_id") != thread_id:
    load_conversation(thread_id)
    st.session_state["loaded_thread_id"] = thread_id

# ----------------------
# Sidebar
# ----------------------

st.sidebar.title("LangGraph PDF Chatbot")
st.sidebar.caption(
    f"Signed in as `{st.session_state['current_user']['email']}`"
)
st.sidebar.markdown(f"**Thread ID:** `{thread_id}`")

if st.sidebar.button("Logout", use_container_width=True):
    # Revoke the current refresh token, then clear UI state.
    try:
        api_request(
            "POST",
            "/auth/logout",
            retry_after_refresh=False,
            json={
                "refresh_token": (
                    st.session_state["refresh_token"]
                )
            },
        )
    finally:
        clear_authentication()
        st.rerun()

if st.sidebar.button("New Chat", use_container_width=True):
    new_thread_id = create_thread()

    if new_thread_id:
        st.session_state["thread_id"] = new_thread_id
        st.session_state["loaded_thread_id"] = None
        st.session_state["message_history"] = []
        st.session_state["awaiting_approval"] = False
        st.session_state["pending_interrupt_msg"] = None
        st.session_state["uploaded_files"] = {}
        st.rerun()

uploaded_pdf = st.sidebar.file_uploader(
    "Upload a PDF for this chat",
    type=["pdf"],
)

uploaded_files = st.session_state["uploaded_files"].setdefault(
    thread_id,
    set(),
)

if uploaded_pdf and uploaded_pdf.name not in uploaded_files:
    with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
        response = api_request(
            "POST",
            f"/threads/{thread_id}/documents",
            files={
                "file": (
                    uploaded_pdf.name,
                    uploaded_pdf.getvalue(),
                    "application/pdf",
                )
            },
        )

        if response.status_code == 200:
            document = response.json()["document"]

            uploaded_files.add(uploaded_pdf.name)

            status_box.update(
                label=(
                    f"Indexed `{document['filename']}` "
                    f"({document['chunks']} chunks)"
                ),
                state="complete",
                expanded=False,
            )
        else:
            status_box.update(
                label="PDF indexing failed",
                state="error",
                expanded=False,
            )
            st.sidebar.error(
                response.json().get(
                    "detail",
                    "Could not index the PDF.",
                )
            )

st.sidebar.subheader("Past conversations")

for thread in threads:
    selected_thread_id = thread["thread_id"]
    label = (
        thread["title"]
        or f"Chat · {selected_thread_id[:8]}…"
    )

    if st.sidebar.button(
        label,
        key=f"thread-{selected_thread_id}",
    ):
        st.session_state["thread_id"] = selected_thread_id
        st.session_state["loaded_thread_id"] = None
        st.rerun()

# ----------------------
# Chat display
# ----------------------

st.title("Multi Utility Chatbot")

for message in st.session_state["message_history"]:
    if message["role"] == "tool":
        with st.expander("Tool result", expanded=False):
            st.text(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.text(message["content"])

# ----------------------
# Human approval controls
# ----------------------

if st.session_state["awaiting_approval"]:
    interrupt_message = (
        st.session_state["pending_interrupt_msg"]
        or "Approval required."
    )

    st.warning(
        f"⏸️ **Action requires your approval**\n\n"
        f"> {interrupt_message}"
    )

    yes_column, no_column = st.columns(2)

    for decision, column, label, button_type in [
        ("yes", yes_column, "Yes, approve", "primary"),
        ("no", no_column, "No, cancel", "secondary"),
    ]:
        with column:
            if st.button(
                label,
                use_container_width=True,
                type=button_type,
            ):
                with st.spinner("Resuming…"):
                    response = api_request(
                        "POST",
                        f"/threads/{thread_id}/approval",
                        json={"decision": decision},
                    )

                if response.status_code == 200:
                    conversation = response.json()

                    st.session_state["message_history"] = (
                        conversation["messages"]
                    )
                    st.session_state["awaiting_approval"] = bool(
                        conversation["pending_interrupt"]
                    )
                    st.session_state["pending_interrupt_msg"] = (
                        conversation["pending_interrupt"]
                    )
                    st.rerun()

                st.error(
                    response.json().get(
                        "detail",
                        "Could not resume the chat.",
                    )
                )

# ----------------------
# Chat input
# ----------------------

user_input = st.chat_input(
    "Ask about your document or use tools",
    disabled=st.session_state["awaiting_approval"],
)

if user_input and not st.session_state["awaiting_approval"]:
    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.text(user_input)

    with st.chat_message("assistant"):
        ai_reply = st.write_stream(
            stream_agent_reply(thread_id, user_input)
        )

    if ai_reply:
        st.session_state["message_history"].append(
            {
                "role": "assistant",
                "content": ai_reply,
            }
        )

    # Show the approval banner immediately after a paused stock action.
    if st.session_state["awaiting_approval"]:
        st.rerun()