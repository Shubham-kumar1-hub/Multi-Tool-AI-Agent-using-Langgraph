from __future__ import annotations

import asyncio
import sys
import os
import tempfile
import requests

from psycopg import connect
from psycopg.rows import dict_row


from typing import Annotated, Any, Dict, Optional, TypedDict

from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_postgres import PGEngine, PGVectorStore

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt, Command

# Psycopg async connections need this event loop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

import time

_stock_price_cache: Dict[str, tuple] = {}
STOCK_CACHE_TTL = 60  # seconds

_search_cache: Dict[str, tuple] = {}
SEARCH_CACHE_TTL = 300  # seconds

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_tokens=2500,
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# -------------------
# pgvector PDF retriever store
# -------------------

VECTOR_TABLE_NAME = "document_chunks"

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from your .env file.")

if DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )
else:
    raise RuntimeError(
        "DATABASE_URL must start with postgresql://"
    )

# Creates a reusable PostgreSQL connection pool for vector operations.
pg_engine = PGEngine.from_connection_string(
    url=SQLALCHEMY_DATABASE_URL
)

pdf_vector_store = PGVectorStore.create_sync(
    engine=pg_engine,
    table_name=VECTOR_TABLE_NAME,
    embedding_service=embeddings,
    metadata_columns=["thread_id"],
)

_THREAD_METADATA: Dict[str, dict] = {}

def _get_retriever(thread_id: Optional[str]):
    """
    Return a retriever that searches only inside this chat thread's PDF chunks.

    This preserves MMR retrieval settings:
    - return 4 final chunks
    - fetch 12 candidate chunks for diverse results 
    """

    if not thread_id:
        return None

    return pdf_vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 4,
            "fetch_k": 12,
            "filter": {"thread_id": str(thread_id)},
        },
    )


def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None):

    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")
    
    # Saves the uploaded pdf bytes as a real .pdf file so it can be used by PyPDFLoader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name
 
    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
 
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = splitter.split_documents(docs)
 
        # ---------- CLEAN TEXT ----------
        texts = []
        metadatas = []
 
        for doc in chunks:
            text = doc.page_content
 
            if text is None:
                continue
 
            # Stripping  spaces
            text = str(text).strip()

            # Removing null bytes and non-UTF-8 characters that break the tokenizer
            text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

            # Striping control characters (except newlines and tabs) that cause TextEncodeInput errors
            text = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
            text = text.strip()

            if len(text) == 0:
                continue
 
            texts.append(text)
            # Keep page metadata and attach this chunk to the current chat thread.
            chunk_metadata = dict(doc.metadata)
            chunk_metadata["thread_id"] = str(thread_id)
            chunk_metadata["source_file"] = filename or os.path.basename(temp_path)

            metadatas.append(chunk_metadata)
 
        if len(texts) == 0:
            raise ValueError("No valid text extracted from the PDF")
        
        # ---------- PGVECTOR STORE ----------

        thread_key = str(thread_id)


        pdf_vector_store.delete(
            filter={"thread_id": thread_key}
        )
 
        # Embeds the chunks and stores them permanently in PostgreSQL + pgvector.
        pdf_vector_store.add_texts(
            texts=texts,
            metadatas=metadatas,
        )
 
        _THREAD_METADATA[str(thread_id)] = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(texts),
        }
 
        return {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(texts),
        }
 
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass



# -------------------
# Tools
# -------------------
 
_raw_search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def search_tool(query: str) -> str:
    """Search the web for current information, news, or general queries."""
    cached = _search_cache.get(query)
    if cached:
        result, timestamp = cached
        if time.time() - timestamp < SEARCH_CACHE_TTL:
            return result

    result = _raw_search_tool.run(query)
    _search_cache[query] = (result, time.time())
    return result
 
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Performing a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
 
        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}
 
 
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage. Returns price data or a descriptive error.
    """

    cached = _stock_price_cache.get(symbol)
    if cached:
        result, timestamp = cached
        if time.time() - timestamp < STOCK_CACHE_TTL:
            return result
    if not API_KEY:
        return {"error": "ALPHA_VANTAGE_API_KEY is not configured on the server."}
 
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
        )

        # Calling API
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        data = r.json()

        # Extracting Stock data
        quote = data.get("Global Quote", {})
        if not quote:
            return {
                "error": (
                    f"No data found for symbol '{symbol}'. "
                    "Check the ticker or try again later."
                )
            }
 
        result = {
            "symbol": quote.get("01. symbol", symbol),
            "price": quote.get("05. price"),
            "open": quote.get("02. open"),
            "high": quote.get("03. high"),
            "low": quote.get("04. low"),
            "volume": quote.get("06. volume"),
            "latest_trading_day": quote.get("07. latest trading day"),
            "previous_close": quote.get("08. previous close"),
            "change": quote.get("09. change"),
            "change_percent": quote.get("10. change percent"),
        }
        _stock_price_cache[symbol] = (result, time.time())
        return result
 
    except requests.Timeout:
        return {"error": "Request timed out while fetching stock data. Try again."}
    except requests.RequestException as e:
        return {"error": f"Network error fetching stock data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def validate_trade_params(symbol: str, quantity: int) -> str | None:
    """Returns an error message if params are unsafe, else None."""

    import re

    if not re.fullmatch(r"[A-Z]{1,5}", symbol):
        return f"'{symbol}' is not a valid stock symbol format."

    if quantity <= 0 or quantity > 10000:
        return f"Quantity {quantity} is outside the allowed range (1-10000)."

    return None
 
 
@tool
def purchase_stock(symbol: str, quantity: int) -> dict:
    """
    Simulate purchasing a given quantity of a stock symbol.
 
    HUMAN-IN-THE-LOOP:
    Before confirming the purchase, this tool will interrupt
    and wait for a human decision ("yes" / anything else).
    """

    error = validate_trade_params(symbol, quantity)
    if error:
        return {"status": "rejected", "message": error}
 
    # This pauses the graph and returns control to the owner.
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")
 
    if isinstance(decision, str) and decision.lower() == "yes":
        return {
            "status": "success",
            "message": f"Purchase order placed for {quantity} shares of {symbol}.",
            "symbol": symbol,
            "quantity": quantity,
        }
    else:
        return {
            "status": "cancelled",
            "message": f"Purchase of {quantity} shares of {symbol} was declined by the owner.",
            "symbol": symbol,
            "quantity": quantity,
        }
 
 
@tool
def sell_stock(symbol: str, quantity: int) -> dict:
    """
    Simulate selling a given quantity of a stock symbol.
 
    HUMAN-IN-THE-LOOP:
    Before confirming the sale, this tool will interrupt
    and wait for a human decision ("yes" / anything else).
    """

    error = validate_trade_params(symbol, quantity)
    if error:
        return {"status": "rejected", "message": error}
    
    # This pauses the graph and returns control to the caller
    decision = interrupt(f"Approve selling {quantity} shares of {symbol}? (yes/no)")
 
    if isinstance(decision, str) and decision.lower() == "yes":
        return {
            "status": "success",
            "message": f"Sell order placed for {quantity} shares of {symbol}.",
            "symbol": symbol,
            "quantity": quantity,
        }
    else:
        return {
            "status": "cancelled",
            "message": f"Sale of {quantity} shares of {symbol} was declined by the owner.",
            "symbol": symbol,
            "quantity": quantity,
        }
 
 
@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    Returns source page numbers alongside the extracted context.
    """
    retriever = _get_retriever(thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }
 
    result = retriever.invoke(query)
 
    # Including page citations so users can verify the source
    context = [
        f"[Page {doc.metadata.get('page', '?')}]: {doc.page_content}"
        for doc in result
    ]
    metadata = [doc.metadata for doc in result]
 
    return {
        "query": query,
        "context": context,
        "metadata": metadata,
        "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }
 
 
tools = [search_tool, get_stock_price, purchase_stock, sell_stock, calculator, rag_tool]
 
llm_with_tools = llm.bind_tools(tools)
 
# -------------------
# State
# -------------------
 
 
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: Optional[str]
    uploaded_filename: Optional[str]   # track which document is loaded
    tool_call_count: int               # guard against infinite tool loops
 
 
# -------------------
# Nodes
# -------------------
 
MAX_TOOL_CALLS = 10
 
 
def chat_node(state: ChatState, config=None):
 
    thread_id = state.get("thread_id")
 
    # Fallback: read from config if state doesn't have it yet
    if not thread_id and config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")
 
    # Guard against infinite tool-call loops
    tool_call_count = state.get("tool_call_count", 0)
    if tool_call_count > MAX_TOOL_CALLS:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I've made too many tool calls trying to answer your question. "
                        "Please rephrase or break it into smaller steps."
                    )
                )
            ],
            "tool_call_count": 0,
        }
 
    uploaded_filename = (
        state.get("uploaded_filename", "")
        or _THREAD_METADATA.get(str(thread_id), {}).get("filename", "")
    )
 
    doc_hint = (
        f"A PDF named '{uploaded_filename}' is indexed for this thread. "
        "Use rag_tool to answer document questions."
        if uploaded_filename
        else "No PDF has been uploaded for this thread yet."
    )
 
    system_message = SystemMessage(
        content=(
            "You are a multi-tool financial and document assistant.\n\n"
            "TOOLS AVAILABLE:\n"
            "- rag_tool: Answer questions from the uploaded PDF. Always pass thread_id.\n"
            "- get_stock_price: Get real-time stock prices by ticker symbol. Never guess prices.\n"
            "- purchase_stock: Simulate buying stocks — requires human approval.\n"
            "- sell_stock: Simulate selling stocks — requires human approval.\n"
            "- calculator: Arithmetic operations (add / sub / mul / div).\n"
            "- search_tool: Search the web for current information.\n\n"
            "RULES:\n"
            "- Always use rag_tool for document questions, not your own knowledge.\n"
            "- Never guess stock prices — always call get_stock_price.\n"
            f"- Current thread_id is `{thread_id}` — include it in every rag_tool call.\n"
            f"- {doc_hint}\n"
            "- Keep answers concise by default (2-4 sentences or a short list). "
            "Only give a longer, detailed, or tabular answer if the user explicitly "
            "asks for more detail, a full breakdown, or a summary.\n"
        )
    )
 
    messages = [system_message, *state["messages"]]
 
    response = llm_with_tools.invoke(messages, config=config)

    new_tool_calls = len(response.tool_calls) if response.tool_calls else 0

    updated_count = 0 if new_tool_calls == 0 else tool_call_count + new_tool_calls
 
    return {
        "messages": [response],
        "thread_id": thread_id,
        "tool_call_count": updated_count,
    }
 
 
tool_node = ToolNode(tools)

# -------------------
# Checkpointer
# -------------------

# Reads the connection URL from .env.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from your .env file.")
 
conn = connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row,
)

checkpointer = PostgresSaver(conn)

# Creates the checkpoint tables (checkpoints, checkpoint_writes, etc.) 
checkpointer.setup()
 
# -------------------
# Graph
# -------------------
 
graph = StateGraph(ChatState)
 
graph.add_node("chat_node", chat_node)
 
graph.add_node("tools", tool_node)
 
graph.add_edge(START, "chat_node")
 
graph.add_conditional_edges("chat_node", tools_condition)
 
graph.add_edge("tools", "chat_node")
 
chatbot = graph.compile(checkpointer=checkpointer)
 
# -------------------
# Helpers
# -------------------
 
 
def retrieve_all_threads():
 
    all_threads = set()
 
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
 
    return list(all_threads)
 
 
def thread_has_document(thread_id: str) -> bool:
 
    """Return True when PostgreSQL contains at least one chunk for this thread."""

    stored_chunks= pdf_vector_store.get(
        where={"thread_id": str(thread_id)},
        limit=1,
    )

    return bool(stored_chunks.get("ids"))
 
 
def thread_document_metadata(thread_id: str) -> dict:
 
    return _THREAD_METADATA.get(str(thread_id), {})
 
 
def get_pending_interrupt(thread_id: str) -> str | None:
    """
    Returns the interrupt message if the thread is currently paused
    at a human-in-the-loop checkpoint, otherwise None.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = chatbot.get_state(config)
 
    # LangGraph stores pending interrupts in state.tasks
    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0].value  # the message string from interrupt()
    return None
 
 
def resume_with_decision(thread_id: str, decision: str) -> dict:
    """
    Resume a paused graph by providing the human's decision.
    Pass decision="yes" to approve, anything else to cancel.
 
    Returns the assistant's final response messages.
    """
    config = {"configurable": {"thread_id": thread_id}}
 
    # Command(resume=...) feeds the decision back into interrupt()
    events = chatbot.stream(
        Command(resume=decision),
        config=config,
        stream_mode="values",
    )
 
    last_state = None
    for event in events:
        last_state = event
 
    if last_state is None:
        return {"messages": []}
 
    return last_state
 
 
def is_thread_interrupted(thread_id: str) -> bool:
    """
    Quick boolean check — is this thread currently waiting for human input?
    """
    return get_pending_interrupt(thread_id) is not None
 
 
def generate_thread_title(first_message: str) -> str:
    """
    Ask the LLM to produce a short (≤5 word) title for a new conversation
    based on the user's first message. Falls back to a truncated snippet
    if the LLM call fails.
    """
    try:
        response = llm.invoke(
            f"Give a concise title of at most 5 words for a conversation that starts with: "
            f'"{first_message}". Reply with only the title, no punctuation.'
        )
        title = response.content.strip().strip('"').strip("'")
        return title if title else first_message[:40]
    except Exception:
        return first_message[:40]
 
 
def send_message(thread_id: str, user_input: str) -> dict:
    """
    Send a normal message to the chatbot (non-interrupted thread).
    Raises RuntimeError if the thread is currently awaiting HITL approval.
    """
    if is_thread_interrupted(thread_id):
        pending = get_pending_interrupt(thread_id)
        raise RuntimeError(
            f"Thread `{thread_id}` is awaiting human approval:\n{pending}\n"
            "Call `resume_with_decision(thread_id, 'yes'/'no')` to continue."
        )
 
    config = {"configurable": {"thread_id": thread_id}}
 
    events = chatbot.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        stream_mode="values",
    )
 
    last_state = None
    for event in events:
        last_state = event
 
    return last_state