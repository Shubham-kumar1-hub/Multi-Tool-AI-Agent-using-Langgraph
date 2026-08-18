# Multi-Tool AI Agent with Human-in-the-Loop

A stateful multi-tool AI agent built with LangGraph that combines RAG over PDFs, real-time stock data, web search, and financial transaction simulation all with a Human-in-the-Loop approval system for sensitive actions.

[![Python](https://img.shields.io/badge/Python-3.12.7-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1.10-green)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3.3--70b-orange)](https://groq.com/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20pgvector-336791)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io/)

---

## 🚀 What It Does

This project is an advanced conversational AI agent capable of managing long-term contexts, integrating with databases, and safely executing workflows. You can:
- **Chat with your PDFs:** Upload documents and ask questions with exact page citations.
- **Get Real-Time Stock Data:** Fetch live pricing for any stock ticker symbol (e.g., AAPL, NVDA).
- **Simulate Stock Trades (HITL):** Initiate "buy" or "sell" orders that pause the AI's thought process, waiting for your explicit human approval before proceeding.
- **Search the Web:** Dynamically retrieve the latest news and facts.
- **Manage Private Threads:** Sign up, log in securely, and switch between your isolated, persistent chat histories.

---

## ✨ Key Features & Architecture

### 1. RAG Pipeline with PostgreSQL & pgvector
Migrated from local FAISS to a robust **PostgreSQL + pgvector** architecture. 
- PDFs are parsed using `PyPDFLoader` and chunked via `RecursiveCharacterTextSplitter`.
- Chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- `pgvector` seamlessly stores embeddings, allowing for efficient Maximum Marginal Relevance (MMR) similarity searches.

### 2. Human-in-the-Loop (HITL) Execution
Using LangGraph's state graph, any call to the `purchase_stock` or `sell_stock` tools interrupts the agent.
- **Graph Pauses:** The Streamlit frontend intercepts the `interrupt()` signal.
- **Human Approval:** The user is presented with a UI banner to ✅ Approve or ❌ Cancel.
- **Graph Resumes:** The user's decision is fed back into the graph via `Command(resume=decision)`.

### 3. FastAPI & JWT Security Layer
The agent backend is wrapped in a secure **FastAPI** service.
- Features complete JWT-based authentication (short-lived access tokens, long-lived SHA-256 hashed refresh tokens).
- Users can only access and query data from threads they own.
- Chat streaming utilizes Server-Sent Events (SSE) to render agent tokens and tool calls in real-time.

### 4. Stateful Conversation Memory
LangGraph integrates tightly with `PostgresSaver`. Every chat thread is fully persisted in PostgreSQL, meaning users can refresh the page, log out, or restart the server without losing their context or pending approvals.

---

## 🧰 Tools Available to the Agent

| Tool Name | Description | Requires Approval |
| :--- | :--- | :---: |
| `rag_tool` | Retrieves relevant text chunks from the user's uploaded PDF using MMR search. | ❌ No |
| `get_stock_price` | Fetches real-time stock data from the Alpha Vantage API. | ❌ No |
| `purchase_stock` | Simulates purchasing shares. Agent cannot proceed without user input. | ✅ Yes |
| `sell_stock` | Simulates selling shares. Agent cannot proceed without user input. | ✅ Yes |
| `calculator` | Performs exact arithmetic (add, sub, mul, div) to avoid LLM math hallucinations. | ❌ No |
| `duckduckgo_search`| Searches the web for up-to-date knowledge and news. | ❌ No |

---

## 🧪 Evaluation Framework

The project includes an automated evaluation pipeline (`eval/` directory) to guarantee agent reliability:
- **`golden_dataset.py`**: Defines strict Q&A scenarios (e.g., verifying the agent correctly picks the `calculator` for math, or `rag_tool` for document summaries).
- **`eval_guardrails.py`**: Simulates prompt injections (e.g., "ignore previous instructions") to ensure the `ChatRequest` Pydantic models block malicious inputs. Validates stock parameters (preventing trades of >10,000 shares).
- **`run_report.py`**: Executes the testing suite and outputs a pass/fail diagnostic report of tool usage and keyword matching.

---

## 💻 Tech Stack

- **LLM:** Groq (`llama-3.3-70b-versatile`)
- **Agent Orchestration:** LangGraph
- **Backend API:** FastAPI, Pydantic
- **Database:** PostgreSQL (with `pgvector` extension)
- **Embeddings:** HuggingFace (`all-MiniLM-L6-v2`)
- **Frontend:** Streamlit
- **Containerization:** Docker & Docker Compose

---

## 📂 Project Structure

```bash
.
├── api/
│   └── main.py                   # FastAPI application & JWT Auth routes
├── eval/                         # Evaluation pipeline
│   ├── eval_agent.py             # Agent execution tests
│   ├── eval_guardrails.py        # Security & prompt injection tests
│   ├── golden_dataset.py         # Baseline test cases
│   └── run_report.py             # Main evaluation script
├── images/                       # UI Screenshots
├── Agent_backend.py              # LangGraph definition, RAG, & Tools
├── Agent_frontend.py             # Streamlit UI
├── docker-compose.yml            # PostgreSQL + pgvector container config
├── Dockerfile                    # Application containerization
├── requirements.txt              # Python dependencies
├── setup_auth_tables.py          # DB Migration: Users
├── setup_auth_security_tables.py # DB Migration: Refresh tokens
├── setup_thread_tables.py        # DB Migration: Thread ownership
└── setup_vector_store.py         # DB Migration: pgvector document_chunks
```

---

## 🏁 Getting Started (End-to-End Guide)

Follow these steps to run the complete stack on your local machine.

### 1. Prerequisites
- Python 3.12+
- Docker Desktop
- [Groq API Key](https://console.groq.com/) (Free)
- [Alpha Vantage API Key](https://www.alphavantage.co/) (Free)

### 2. Clone the Repository
```bash
git clone https://github.com/Shubham-kumar1-hub/Agent-using-Langgraph.git
cd Agent-using-Langgraph
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
DATABASE_URL=postgresql://agent_user:change_me_local_only@localhost:5433/multi_tool_agent
JWT_SECRET_KEY=generate_a_random_secure_string_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
API_BASE_URL=http://127.0.0.1:8000
```

### 4. Start the PostgreSQL Database
Spin up the `pgvector` container using Docker Compose:
```bash
docker-compose up -d
```

### 5. Run Database Migrations
Initialize your database schemas and vector tables:
```bash
python setup_auth_tables.py
python setup_auth_security_tables.py
python setup_thread_tables.py
python setup_vector_store.py
```

### 6. Start the FastAPI Backend
In a new terminal window, start the secure backend API:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Start the Streamlit Frontend
In a separate terminal window, launch the UI:
```bash
streamlit run Agent_frontend.py
```
*Navigate to `http://localhost:8501` to create an account and begin chatting!*

---
*Developed by Shubham Kumar*