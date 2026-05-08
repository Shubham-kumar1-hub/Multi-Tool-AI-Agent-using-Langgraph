# Multi-Tool AI Agent with Human-in-the-Loop

A stateful multi-tool AI agent built with LangGraph that combines RAG over PDFs, real-time stock data, web search, and financial transaction simulation all with a Human-in-the-Loop approval system for sensitive actions.

[![Python](https://img.shields.io/badge/Python-3.12.7-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1.10-green)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3.3--70b-orange)](https://groq.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)

---

## Live Demo

- **App:** https://agent-using-langgraph-k5zkvjcidrcdryg9q5fxbu.streamlit.app/
- **GitHub:** https://github.com/Shubham-kumar1-hub/Multi-Tool-AI-Agent-using-Langgraph

---

## What It Does

This project is a multi-tool conversational AI agent where the user can:

- **Chat with their PDF** -> upload any PDF and ask questions about it
- **Get real-time stock prices** -> fetch live data for any ticker symbol (AAPL, TSLA, etc.)
- **Buy / Sell stocks** -> simulate financial trades with human approval required before execution
- **Search the web** -> get current information via DuckDuckGo
- **Do calculations** -> arithmetic operations through a dedicated calculator tool
- **Switch between conversations** -> all chats are persisted and resumable

---

## Key Features

### Human-in-the-Loop (HITL)
The most unique feature of this project. When the agent wants to execute a stock purchase or sale, the graph **pauses completely** and waits for the user to approve or reject the action before continuing. This is implemented using LangGraph's `interrupt()` and `Command(resume=...)` pattern.

```
User: "Buy 10 shares of AAPL"
Agent: calls purchase_stock tool
Graph: ⏸️ PAUSED — waiting for human approval
User: clicks ✅ Yes or ❌ No
Graph: ▶️ RESUMES with the decision
Agent: confirms or cancels the order
```

### RAG Pipeline
- PDFs are uploaded via the sidebar and chunked using `RecursiveCharacterTextSplitter`
- Chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2`
- Stored and retrieved using FAISS with **MMR (Maximum Marginal Relevance)** for diverse, non-redundant results
- FAISS indexes are **persisted to disk** per thread — survive backend restarts
- Responses include **page citations** so users can verify sources

### Stateful Conversations
- Every conversation is a separate **thread** with its own UUID
- Conversation history is persisted using **SQLite checkpointing** via LangGraph
- Threads survive page refreshes and app restarts
- Past conversations are accessible from the sidebar

### Tool Call Safety
- Agent is limited to **10 tool calls per turn** to prevent infinite loops
- All tool errors are handled gracefully and returned as descriptive messages

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Streamlit Frontend            │
│  Sidebar: PDF upload, thread switcher   │
│  Main: Chat UI + HITL approval banner   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│          LangGraph Agent Graph          │
│                                         │
│   START → chat_node ──► tools_condition │
│               ▲              │          │
│               └──── tools ◄──┘          │
└────────────────────┬────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌──────────┐
   │  Groq   │  │  FAISS  │  │  SQLite  │
   │ Llama3.3│  │ Vectors │  │ History  │
   └─────────┘  └─────────┘  └──────────┘
```

### Tools Available to the Agent

| Tool | Description |
|---|---|
| `rag_tool` | Retrieves relevant chunks from the uploaded PDF |
| `get_stock_price` | Fetches real-time stock data from Alpha Vantage |
| `purchase_stock` | Simulates buying stocks — triggers HITL approval |
| `sell_stock` | Simulates selling stocks — triggers HITL approval |
| `calculator` | Performs arithmetic (add, sub, mul, div) |
| `duckduckgo_search` | Searches the web for current information |

---

## Tech Stack

| Category | Technology |
|---|---|
| LLM | Groq — Llama 3.3 70B Versatile |
| Agent Framework | LangGraph |
| RAG | FAISS + HuggingFace Embeddings |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| PDF Parsing | PyPDFLoader |
| Web Search | DuckDuckGo |
| Stock API | Alpha Vantage |
| Frontend | Streamlit |
| Persistence | SQLite (conversations) + FAISS on disk (vectors) |
| Containerization | Docker + Docker Compose |
| Language | Python 3.12.7 |

---

## Project Structure

```
Agent-using-Langgraph/
├── Agent_backend.py       # LangGraph graph, tools, RAG, HITL logic
├── Agent_frontend.py      # Streamlit UI
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── .dockerignore          # Files excluded from Docker image
├── .gitignore             # Files excluded from Git
├── .env                   # API keys (never committed)
├── faiss_indexes/         # FAISS vector stores (auto-created)
└── chatbot.db             # SQLite conversation history (auto-created)
```

---

## Getting Started

### Prerequisites
- Python 3.12.7
- A [Groq API key](https://console.groq.com/) (free)
- An [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key) (free)

### Option 1 — Run with Docker (Recommended)

**Step 1:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Step 2:** Clone the repository
```bash
git clone https://github.com/Shubham-kumar1-hub/Agent-using-Langgraph.git
cd Agent-using-Langgraph
```

**Step 3:** Create your `.env` file
```bash
GROQ_API_KEY=your_groq_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

**Step 4:** Build and run
```bash
docker-compose up --build
```

**Step 5:** Open your browser
```
http://localhost:8501
```

---

### Option 2 — Run Locally

**Step 1:** Clone the repository
```bash
git clone https://github.com/Shubham-kumar1-hub/Agent-using-Langgraph.git
cd Agent-using-Langgraph
```

**Step 2:** Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**Step 3:** Install dependencies
```bash
pip install -r requirements.txt
```

**Step 4:** Create your `.env` file
```
GROQ_API_KEY=your_groq_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

**Step 5:** Run the app
```bash
streamlit run Agent_frontend.py
```

**Step 6:** Open your browser
```
http://localhost:8501
```

---

## Docker Commands

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build
```

---

## How to Use

**Chat normally**
Just type any question in the chat input box.

**Ask about a PDF**
1. Upload a PDF using the sidebar file uploader
2. Ask any question about its content — the agent will retrieve relevant chunks automatically

**Get stock prices**
```
"What is the current price of TSLA?"
"Show me AAPL stock data"
```

**Simulate a stock trade**
```
"Buy 5 shares of MSFT"
"Sell 10 shares of GOOGL"
```
The app will pause and show an approval banner — click ✅ Yes or ❌ No.

**Search the web**
```
"What are the latest AI news today?"
"Who is the CEO of OpenAI?"
```

**Calculate**
```
"What is 1250 multiplied by 3.5?"
"Divide 9500 by 4"
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key from console.groq.com |
| `ALPHA_VANTAGE_API_KEY` | ✅ Yes | Your Alpha Vantage key for stock data |

---

## Known Limitations

- **FAISS** is an in-memory vector store — does not support multiple concurrent users at scale
- **Streamlit** is single-threaded — not suitable for high production traffic
- **No authentication** — all users share the same session namespace
- **SQLite** is file-based — not suitable for distributed deployments

For production scale these would be replaced with Pinecone, FastAPI, Supabase Auth, and PostgreSQL.

---

## Author

**Shubham Kumar**
- GitHub: [@Shubham-kumar1-hub](https://github.com/Shubham-kumar1-hub)
