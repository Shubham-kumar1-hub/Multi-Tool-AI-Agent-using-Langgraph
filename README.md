# Multi-Tool AI Agent with Human-in-the-Loop

A conversational AI agent built with LangGraph that can search the web, do calculations, check stock prices, answer questions from uploaded PDFs, and even buy/sell stocks — but pauses and asks for human approval before doing anything financial.

---

## What this project does

You chat with the agent, and depending on what you ask, it decides which tool to use:

- **Web search** — for general/current-event questions
- **Calculator** — for math
- **Stock price lookup** — pulls live stock prices
- **RAG (PDF Q&A)** — upload a PDF, ask questions about it, the agent retrieves relevant chunks and answers from them
- **Buy/Sell stock** — before executing, it pauses and waits for the user to approve or reject the trade (this is the "human-in-the-loop" part)

---

## Tech Stack

| Layer | What I used |
|---|---|
| Agent framework | LangGraph |
| LLM | Groq (openai/gpt-oss-120b) |
| Conversation memory | PostgreSQL via `PostgresSaver` (LangGraph checkpointer) |
| Vector database (RAG) | pgvector (PostgreSQL extension) |
| Backend API | FastAPI |
| Authentication | JWT (access + refresh tokens), Argon2 password hashing |
| Frontend | Streamlit |
| Observability | LangSmith |
| Containerization | Docker (for the Postgres + pgvector database) |

---

## Why I built it this way

**Started simple, upgraded step by step:**
- Started with SQLite for saving conversation history → migrated to **PostgreSQL** so it can actually scale and handle multiple users properly
- Started with FAISS (in-memory vector store) → migrated to **pgvector** so embeddings persist in the database instead of disappearing every restart
- Added **JWT authentication** so each user only sees their own conversations
- Added **guardrails** to block obvious prompt injection attempts and stop unsafe trade requests (like buying 99,999 shares) before they even reach the human approval step
- Added an **automated evaluation script** so I can check if the agent is calling the right tools and giving correct answers, instead of manually testing every time I change something
- Added **LangSmith tracing** so I can see exactly what the agent is doing step-by-step, and debug/optimize it properly

---

## Project Structure

```
Agent uisng Langgraph/
├── .devcontainer/
├── .vscode/
├── Agent/
├── api/
├── eval/
│   ├── eval_agent.py         # runs test questions through the agent automatically
│   ├── eval_guardrails.py    # tests guardrails in isolation
│   ├── golden_dataset.py     # list of test questions + expected answers
│   ├── run_report.py         # prints pass/fail results
│   └── sample.pdf            # test file used for the RAG eval case
├── images/
├── .dockerignore
├── .env                       # API keys, database URL (not committed to GitHub)
├── .gitignore
├── Agent_backend.py           # the LangGraph agent itself — tools, graph, guardrails
├── Agent_frontend.py          # Streamlit UI
├── agent_metrics.json
├── docker-compose.yml         # spins up Postgres + pgvector locally
├── Dockerfile
├── README.md
├── requirements.txt
├── setup_auth_tables.py            # creates the `users` table
├── setup_auth_security_tables.py   # creates refresh token table + logout support
├── setup_thread_tables.py          # creates table to track which chat belongs to which user
├── setup_vector_store.py           # creates the pgvector table for PDF chunks
└── test_postgres.py           # quick script to sanity-check the DB connection
```

> Note: `chatbot.db` / `chatbot.db-shm` / `chatbot.db-wal` (legacy SQLite files) and `faiss_indexes/` (legacy FAISS index) were removed after migrating to PostgreSQL + pgvector — they're no longer used anywhere in the code.

---

## How to run this locally

1. **Clone the repo and install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the database**
   ```bash
   docker-compose up -d
   ```

3. **Set up your `.env` file** with:
   ```
   DATABASE_URL=postgresql://agent_user:change_me_local_only@localhost:5433/multi_tool_agent
   GROQ_API_KEY=your_key_here
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_key_here
   LANGSMITH_PROJECT=multi-utility-agent
   ```

4. **Run the one-time table setup scripts** (in order)
   ```bash
   python setup_auth_tables.py
   python setup_auth_security_tables.py
   python setup_thread_tables.py
   python setup_vector_store.py
   ```

5. **(Optional) Verify the DB connection**
   ```bash
   python test_postgres.py
   ```

6. **Start the backend**
   ```bash
   uvicorn main:app --reload
   ```

7. **Start the frontend**
   ```bash
   streamlit run Agent_frontend.py
   ```

8. **Run the evaluation suite (optional, checks everything still works)**
   ```bash
   cd eval
   python run_report.py
   python eval_guardrails.py
   ```

---

## Features Checklist

- [x] Multi-tool LangGraph agent (search, calculator, stock price, RAG, trading)
- [x] Human-in-the-loop approval for buy/sell actions
- [x] PostgreSQL-backed conversation memory (checkpointer)
- [x] pgvector-based RAG for PDF question-answering
- [x] JWT authentication with refresh token rotation
- [x] Input guardrails (blocks prompt injection attempts)
- [x] Tool-level guardrails (blocks unsafe trade quantities/invalid stock symbols)
- [x] Automated evaluation suite (tool selection + RAG + guardrail tests)
- [x] LangSmith tracing for observability
- [ ] Output-side guardrails (not implemented yet — scoped out for now)
- [ ] Latency optimization (in progress)

---

## Honest Limitations (things I know aren't perfect yet)

- Guardrails are keyword/rule-based, not semantic — they can be bypassed by rephrasing an attack differently
- The evaluation set is small (~13 test cases) and uses simple keyword matching, not deep answer-quality scoring
- Latency hasn't been optimized yet — this is my current focus using LangSmith traces to find slow points
- No output filtering yet, only input and tool-parameter checks

I'm listing these on purpose — I'd rather be upfront about what's a work-in-progress than pretend it's a finished production system.

---

## About Me

Built by **Shubham Kumar**, final-year B.Tech Computer Engineering student, while learning and job-hunting for AI/ML Engineer roles.

GitHub: [Shubham-kumar1-hub](https://github.com/Shubham-kumar1-hub)