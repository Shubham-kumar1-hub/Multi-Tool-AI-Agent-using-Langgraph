import uuid
from datetime import datetime

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from Agent_backend import (
    chatbot,
    ingest_pdf,
    retrieve_all_threads,
    thread_document_metadata,
    generate_thread_title,
    # -- HITL helpers --
    is_thread_interrupted,
    get_pending_interrupt,
    resume_with_decision,
)


# ---------------------- Utilities ----------------------

def generate_thread_id() -> uuid.UUID:
    return uuid.uuid4()


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    _register_thread(thread_id, title=None)
    st.session_state["message_history"] = []


def _register_thread(thread_id: uuid.UUID, title: str | None = None):
    """Add a thread to the sidebar list if not already present."""
    tid = str(thread_id)
    if tid not in st.session_state["thread_titles"]:
        label = title or f"Chat · {datetime.now().strftime('%b %d %H:%M')} · {tid[:8]}…"
        st.session_state["thread_titles"][tid] = label

    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def load_conversation(thread_id: uuid.UUID) -> list:
    state = chatbot.get_state(config={"configurable": {"thread_id": str(thread_id)}})
    return state.values.get("messages", [])


# ---------------------- Session Initialization ----------------------

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    existing = retrieve_all_threads()
    st.session_state["chat_threads"] = [uuid.UUID(t) if isinstance(t, str) else t for t in existing]

if "thread_titles" not in st.session_state:
    # Build display labels for pre-existing threads
    st.session_state["thread_titles"] = {
        str(t): f"Chat · {str(t)[:8]}…"
        for t in st.session_state["chat_threads"]
    }

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

# Track whether we are awaiting HITL approval
if "awaiting_approval" not in st.session_state:
    st.session_state["awaiting_approval"] = False

if "pending_interrupt_msg" not in st.session_state:
    st.session_state["pending_interrupt_msg"] = None

# Tracking whether a title has been generated for the current thread
if "title_generated" not in st.session_state:
    st.session_state["title_generated"] = set()

_register_thread(st.session_state["thread_id"])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"][::-1]
selected_thread = None

# ------------------------- Sidebar -------------------------
st.sidebar.title("LangGraph PDF Chatbot")
st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")

if st.sidebar.button("New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f"Using `{latest_doc.get('filename')}` "
        f"({latest_doc.get('chunks')} chunks from {latest_doc.get('documents')} pages)"
    )
else:
    st.sidebar.info("No PDF indexed yet.")

uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
    else:
        with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
            summary = ingest_pdf(
                uploaded_pdf.getvalue(),
                thread_id=thread_key,
                filename=uploaded_pdf.name,
            )
            thread_docs[uploaded_pdf.name] = summary
            status_box.update(label=" PDF indexed", state="complete", expanded=False)

st.sidebar.subheader("Past conversations")
if not threads:
    st.sidebar.write("No past conversations yet.")
else:
    for thread_id in threads:
        tid = str(thread_id)
        label = st.session_state["thread_titles"].get(tid, f"Chat · {tid[:8]}…")
        if st.sidebar.button(label, key=f"side-thread-{tid}"):
            selected_thread = thread_id

# ------------------------- Main Layout -------------------------
st.title("Multi Utility Chatbot")

# Render chat history
for message in st.session_state["message_history"]:
    role = message["role"]
    content = message["content"]
    if role == "tool":
        # Render tool messages as a collapsed info block
        with st.expander(f" Tool result", expanded=False):
            st.text(content)
    else:
        with st.chat_message(role):
            st.text(content)

# ---------------------------------------------------------------
#  HITL APPROVAL BANNER
#  Shown whenever the graph is paused waiting for human approval.
#  Sync session state with actual graph state on every render so
#  the banner persists even after a page re-run.
# ---------------------------------------------------------------
if is_thread_interrupted(thread_key):
    st.session_state["awaiting_approval"] = True
    st.session_state["pending_interrupt_msg"] = get_pending_interrupt(thread_key)

if st.session_state["awaiting_approval"]:
    interrupt_msg = st.session_state["pending_interrupt_msg"] or "Approval required."

    st.warning(f"⏸️ **Action requires your approval**\n\n> {interrupt_msg}")

    col_yes, col_no = st.columns(2)

    with col_yes:
        if st.button(" Yes, approve", use_container_width=True, type="primary"):
            with st.spinner("Resuming…"):
                try:
                    final_state = resume_with_decision(thread_key, "yes")
                    ai_reply = ""
                    for msg in reversed(final_state.get("messages", [])):
                        if isinstance(msg, AIMessage) and msg.content:
                            ai_reply = msg.content
                            break
                    st.session_state["message_history"].append(
                        {"role": "assistant", "content": ai_reply}
                    )
                except Exception as e:
                    st.error(f"Error resuming conversation: {e}")

            # Clear HITL flags
            st.session_state["awaiting_approval"] = False
            st.session_state["pending_interrupt_msg"] = None
            st.rerun()

    with col_no:
        if st.button(" No, cancel", use_container_width=True):
            with st.spinner("Cancelling…"):
                try:
                    final_state = resume_with_decision(thread_key, "no")
                    ai_reply = ""
                    for msg in reversed(final_state.get("messages", [])):
                        if isinstance(msg, AIMessage) and msg.content:
                            ai_reply = msg.content
                            break
                    st.session_state["message_history"].append(
                        {"role": "assistant", "content": ai_reply}
                    )
                except Exception as e:
                    st.error(f"Error cancelling: {e}")

            # Clear HITL flags
            st.session_state["awaiting_approval"] = False
            st.session_state["pending_interrupt_msg"] = None
            st.rerun()

# ----------------------------------------------------------------
#  CHAT INPUT  (disabled while awaiting approval)
# -----------------------------------------------------------------
user_input = st.chat_input(
    "Ask about your document or use tools",
    disabled=st.session_state["awaiting_approval"],
)

if user_input and not st.session_state["awaiting_approval"]:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    # Generate a human readable thread title from the first message
    if thread_key not in st.session_state["title_generated"]:
        with st.spinner("Naming conversation…"):
            try:
                title = generate_thread_title(user_input)
                st.session_state["thread_titles"][thread_key] = title
                st.session_state["title_generated"].add(thread_key)
            except Exception:
                pass  # title stays as default; non critical

    CONFIG = {
        "configurable": {"thread_id": thread_key},
        "metadata": {"thread_id": thread_key},
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        status_holder = {"box": None}
        hit_interrupt = {"value": False}

        def ai_only_stream():
            try:
                for message_chunk, _ in chatbot.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode="messages",
                ):
                    if isinstance(message_chunk, ToolMessage):
                        tool_name = getattr(message_chunk, "name", "tool")
                        if status_holder["box"] is None:
                            status_holder["box"] = st.status(
                                f" Using `{tool_name}` …", expanded=True
                            )
                        else:
                            status_holder["box"].update(
                                label=f" Using `{tool_name}` …",
                                state="running",
                                expanded=True,
                            )

                        # Persist tool result in history
                        st.session_state["message_history"].append(
                            {"role": "tool", "content": str(message_chunk.content)}
                        )

                    if isinstance(message_chunk, AIMessage):
                        yield message_chunk.content

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.session_state["awaiting_approval"] = False
                return

            # After streaming ends, check if graph paused for HITL
            if is_thread_interrupted(thread_key):
                hit_interrupt["value"] = True

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(
                label=" Tool finished", state="complete", expanded=False
            )

    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

    # If graph paused mid stream, activate HITL banner
    if hit_interrupt["value"]:
        st.session_state["awaiting_approval"] = True
        st.session_state["pending_interrupt_msg"] = get_pending_interrupt(thread_key)
        st.rerun()

    doc_meta = thread_document_metadata(thread_key)
    if doc_meta:
        st.caption(
            f"Document indexed: {doc_meta.get('filename')} "
            f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
        )

st.divider()

# -------------------------------------------------------
#  THREAD SWITCHING
# -------------------------------------------------------
if selected_thread:
    st.session_state["thread_id"] = selected_thread
    messages = load_conversation(selected_thread)

    temp_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            temp_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            temp_messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, ToolMessage):
            temp_messages.append({"role": "tool", "content": str(msg.content)})

    st.session_state["message_history"] = temp_messages
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()