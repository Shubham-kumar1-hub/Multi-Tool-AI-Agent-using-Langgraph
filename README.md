# Multi-Tool AI Agent with Human-in-the-Loop

A conversational AI agent built with LangGraph that can search the web, do calculations, check stock prices, answer questions from uploaded PDFs, and buy/sell stocks — but pauses and asks for human approval before doing anything financial.


---

## What this project does

- **Web search** — for general/current-event questions
- **Calculator** — add, subtract, multiply, divide
- **Stock price lookup** — live stock prices, with caching to avoid redundant API calls
- **RAG (PDF Q&A)** — upload a PDF, ask questions about it, the agent retrieves relevant chunks and answers from them
- **Buy/Sell stock** — pauses and waits for human approval before executing (the "human-in-the-loop" part), with guardrails on trade quantity and symbol format

---

## Tech Stack

| Layer | What I used |
|---|---|
| Agent framework | LangGraph |
| LLM (agent) | Groq — `openai/gpt-oss-120b` |
| LLM (eval judge) | Google Gemini — `gemini-3.5-flash-lite` (deliberately a different provider than the agent, to avoid the judge being biased toward its own model's reasoning style) |
| Conversation memory | PostgreSQL via `PostgresSaver` (LangGraph checkpointer) |
| Vector database (RAG) | pgvector (PostgreSQL extension), hosted on Neon |
| Backend API | FastAPI |
| Authentication | JWT (access + refresh tokens), Argon2 password hashing |
| Frontend | Streamlit |
| Observability | LangSmith |

---

## Guardrails

Rule-based, not semantic — deliberately kept simple and explainable rather than reaching for an external guardrails library.

- **Input guardrail** — a Pydantic validator on the chat request blocks messages containing known prompt-injection phrases (e.g. "ignore previous instructions") before they ever reach the agent.
- **Trade-param guardrails** — before a buy/sell request reaches human approval, it's checked for a valid stock symbol format and a sane quantity range, rejecting obviously bad trades early.

**Known limitation:** keyword/phrase-based blocking can be bypassed by rephrasing. There's no semantic detection, no output-side guardrail, and no rate limiting. I scoped this deliberately for a v1, not because I think it's a complete solution.

---

## Evaluation Suite

An automated eval suite, not just manual testing — 25 test cases across happy paths, edge cases, and ambiguous input, using two different scoring approaches depending on what's being checked:

- **Deterministic checks** (tool selection, keyword presence) for cases with an objectively correct answer — e.g. did it call `get_stock_price`, does "48" appear in the calculator response.
- **LLM-as-judge** for open-ended answers that keyword matching can't fairly evaluate — e.g. grading whether an explanation of REST vs GraphQL is actually accurate, using a rubric instead of a fixed keyword.
- **Faithfulness checking** for RAG specifically — a component-level metric that compares the agent's final answer against the actual retrieved chunks, flagging claims that aren't backed by the source material (catches hallucination that a general "is this a good answer?" check would miss).

**Real bugs this suite caught, not just theoretical value:**
- The agent was silently doing bitwise XOR math itself and presenting it as calculator output, despite the calculator tool only supporting add/subtract/multiply/divide. Fixed via a system prompt rule.
- A RAG summary combined two facts that were mentioned separately in the source PDF ("supervised learning" and "scikit-learn" discussed in different sections) into an implied connection ("supervised learning with scikit-learn") that the document never actually stated. Left as a documented limitation rather than fixed, since it's a subtle synthesis-hallucination pattern, not a simple prompt fix.

**Known limitations:**
- Application-level (end-to-end, black-box) evaluation, not full component-level. I have faithfulness (generator-side) but no retriever precision/recall against labeled ground truth — that would require manually labeling which chunks should be retrieved per question, which I haven't built.
- The judge itself hasn't been validated against human judgment on any cases — I'm trusting Gemini's grading without a sanity-check sample.
- 25 cases is a reasonable v1 breadth, not comprehensive coverage.

---

## Latency Optimization

Found and fixed using LangSmith tracing, not guesswork — every change here was measured before and after.

**What I found:** the slowest parts weren't tool calls or the LLM's raw speed — they were long, unbounded response generation and repeated identical API calls.

**Fixes applied, with measured results:**
- **`max_tokens` cap + concise-by-default system prompt rule** — cut a 3.9K-token, 3.19s response down to 888 tokens / 1.12s (**-65%**) on the same query, without breaking the agent's ability to give genuinely detailed answers when explicitly asked (verified separately — a request for a "full detailed breakdown" still completes properly under the raised cap).
- **In-memory caching for stock prices (60s TTL) and web search (300s TTL)** — repeated identical queries dropped from ~0.7s to ~0.00s.
- **Reduced RAG retrieval overhead** — lowered the MMR `fetch_k` candidate pool from 20 to 12, cutting retrieval time from 1.00s to 0.48s (**-52%**) without changing the final number of chunks returned to the LLM.

**A real bug found during verification, not before:** my first caching implementation had a `return` statement placed before the cache-save line, meaning the cache-saving code was unreachable dead code — the cache silently never worked despite looking correct. Caught by testing with an isolated script instead of trusting the first "it looks right" pass.

**Known limitation:** tool calls run sequentially, not in parallel, even when a single request needs two independent tools (e.g. stock price + web search). I verified this directly rather than assuming — `ToolNode`'s parallel execution only triggers when the LLM requests multiple tools in one response, and this model tends to call them one at a time. Forcing true parallelism would need custom graph routing, which I've scoped as a future improvement rather than building now.

---

## Project Structure

```
Agent uisng Langgraph/
├── .devcontainer/
├── .vscode/
├── Agent/
├── api/
├── backend/                    # standalone deploy folder (own Dockerfile, for Render/Cloud Run)
├── frontend/                   # standalone deploy folder (own Dockerfile, for Render/Cloud Run)
├── eval/
│   ├── eval_agent.py           # runs test questions through the agent automatically
│   ├── eval_guardrails.py      # tests guardrails in isolation
│   ├── eval_judge.py           # LLM-as-judge + faithfulness checking (Gemini)
│   ├── golden_dataset.py       # 25 test cases: happy paths, edge cases, judge criteria
│   ├── run_report.py           # prints pass/fail results with judge reasoning
│   ├── test_cache.py           # isolated test for stock price / search caching
│   ├── test_judge.py           # isolated test for the LLM-judge function
│   └── sample.pdf              # test file used for the RAG eval case
├── images/
├── .dockerignore
├── .env
├── .gitignore
├── Agent_backend.py             # the LangGraph agent — tools, graph, guardrails, caching
├── Agent_frontend.py            # Streamlit UI
├── agent_metrics.json
├── docker-compose.yml           # local Postgres + pgvector (development only)
├── Dockerfile
├── README.md
├── requirements.txt
├── setup_auth_tables.py
├── setup_auth_security_tables.py
├── setup_thread_tables.py
├── setup_vector_store.py
└── test_postgres.py
```

> `chatbot.db*` (legacy SQLite) and `faiss_indexes/` (legacy FAISS) were removed after migrating to PostgreSQL + pgvector.

---

## How to run this locally

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the database** (or use a hosted Neon Postgres instance instead)
   ```bash
   docker-compose up -d
   ```

3. **Set up `.env`**
   ```
   DATABASE_URL=your_postgres_connection_string
   GROQ_API_KEY=your_key
   GOOGLE_API_KEY=your_key            # for the eval suite's LLM-judge (Gemini)
   ALPHA_VANTAGE_API_KEY=your_key
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_key
   LANGSMITH_PROJECT=multi-utility-agent
   ```

4. **Run the one-time table setup scripts** (in order)
   ```bash
   python setup_auth_tables.py
   python setup_auth_security_tables.py
   python setup_thread_tables.py
   python setup_vector_store.py
   ```

5. **Start the backend and frontend**
   ```bash
   uvicorn api.main:app --reload
   streamlit run Agent_frontend.py
   ```

6. **Run the evaluation suite**
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
- [x] Automated evaluation suite — 25 cases, keyword + LLM-judge + faithfulness checking
- [x] LangSmith tracing for observability
- [x] Latency profiling and optimization (caching, token capping, retrieval tuning) — measured, not assumed
- [ ] Output-side guardrails (scoped out for now)
- [ ] Semantic (non-keyword) guardrail detection
- [ ] Component-level retrieval metrics (precision/recall against labeled ground truth)
- [ ] Parallel tool-call execution (currently sequential by model behavior)

---

## Honest Limitations

I'd rather document these clearly than let the project look more finished than it is:

- Guardrails are rule-based, not semantic — bypassable by rephrasing an attack.
- No output-side content filtering, only input and tool-parameter checks.
- Eval suite is application-level (end-to-end), not full component-level — I have faithfulness checking for the RAG generator, but no retriever precision/recall against labeled ground truth.
- The LLM-judge's grading has not been validated against human judgment on any sample.
- Tool calls execute sequentially, not in parallel, even for independent requests — verified via tracing, not assumed.
- A documented (not fixed) hallucination pattern exists where the agent can combine two independently true facts from a source document into an implied connection the document never actually stated.

---

## About Me

Built by **Shubham Kumar**, final-year B.Tech Computer Engineering student, while learning and job-hunting for AI/ML Engineer roles.

GitHub: [Shubham-kumar1-hub](https://github.com/Shubham-kumar1-hub)