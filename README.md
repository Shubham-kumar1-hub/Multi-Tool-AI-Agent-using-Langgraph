# 🤖 Multi-Utility AI Agent (LangGraph + RAG + HITL)

A **production-style AI agent** built using **LangGraph, LangChain, and Streamlit** that combines:

* 📄 **Document Intelligence (RAG over PDFs)**
* 📊 **Real-time Financial Data**
* 🧠 **Multi-step reasoning with tool usage**
* ⏸️ **Human-in-the-Loop approvals (HITL)**
* 💾 **Persistent memory across conversations**

> 🚀 Designed to demonstrate **real-world agent architecture**, not just LLM prompts.

---

## ✨ Why This Project Stands Out

Most AI chatbot projects are stateless and prompt-based.
This project goes further:

✅ Stateful execution using LangGraph
✅ Tool orchestration with decision-making
✅ Safe automation using human approvals
✅ Persistent memory with checkpointing
✅ Hybrid intelligence (RAG + APIs + reasoning)

👉 This mirrors how **production AI agents** are actually built.

---

## 🏗️ Architecture Overview

```id="arch-diagram"
                ┌───────────────────────────┐
                │       Streamlit UI        │
                │  (Chat + File Upload)     │
                └────────────┬──────────────┘
                             │
                             ▼
                ┌───────────────────────────┐
                │      LangGraph Agent      │
                │     (StateGraph Flow)     │
                └────────────┬──────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   RAG Tool   │    │  Stock API   │    │ Web Search   │
│ (FAISS + PDF)│    │ AlphaVantage │    │ DuckDuckGo   │
└──────────────┘    └──────────────┘    └──────────────┘
        │
        ▼
┌───────────────────────────┐
│ Human-in-the-Loop Control │
│ (Approve / Reject Actions)│
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ Persistent Memory (SQLite)│
└───────────────────────────┘
```

---

## 🧠 Core Capabilities

### 📄 1. Document Question Answering (RAG)

* Upload PDFs per chat thread
* Automatic chunking & embedding
* FAISS vector search with persistence
* Returns **context + source citations**

---

### 📊 2. Financial Intelligence

* Real-time stock data using Alpha Vantage
* Buy/Sell simulation with safety checks

---

### 🛠️ 3. Tool-Oriented Reasoning

The agent dynamically decides when to use:

* 🔎 Web Search
* 🧮 Calculator
* 📊 Stock API
* 📚 RAG Tool

---

### ⏸️ 4. Human-in-the-Loop (HITL)

Critical actions require approval:

```text
"Approve buying 10 shares of AAPL?"
```

✔ Prevents unsafe automation
✔ Mimics real-world AI governance systems

---

### 💾 5. Persistent Conversations

* SQLite checkpointing via LangGraph
* Multi-thread chat support
* Conversations survive restarts

---

## 🔄 How the Agent Works

1. User sends query
2. LangGraph agent evaluates intent
3. Decides:

   * Answer directly OR
   * Call a tool
4. Executes tool (if needed)
5. Returns final response

---

## 💬 Example Interactions

### 📄 RAG Query

```text
User: Summarize the uploaded PDF
→ Agent uses rag_tool
→ Retrieves relevant chunks
→ Generates contextual answer
```

---

### 📊 Stock Query

```text
User: What's the price of TSLA?
→ Calls get_stock_price
→ Returns real-time data
```

---

### 💼 Safe Trading (HITL)

```text
User: Buy 10 shares of AAPL
→ Agent triggers purchase_stock
→ UI asks for approval
→ Executes only if approved
```

---

### 🌐 Web Search

```text
User: Latest news about AI regulations
→ Uses DuckDuckGo search
→ Returns summarized results
```

---

## 📁 Project Structure

```id="project-structure"
.
├── Agent_backend.py      # LangGraph agent, tools, RAG pipeline
├── Agent_frontend.py     # Streamlit UI + HITL handling
├── requirements.txt      # Dependencies
├── .gitignore
├── chatbot.db            # SQLite memory (auto-created)
└── faiss_indexes/        # Vector DB storage (auto-created)
```

---

## ⚙️ Setup & Installation

### 1️⃣ Clone the Repo

```bash
git clone https://github.com/Shubham-kumar1-hub/Agent-using-Langgraph.git
cd Agent-using-Langgraph
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Add Environment Variables

Create `.env` file:

```env
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

---

## ▶️ Run the App

```bash
streamlit run Agent_frontend.py
```

---

## 🧩 Tech Stack

* **LLM**: Groq (LLaMA 3.3 70B)
* **Frameworks**: LangChain + LangGraph
* **UI**: Streamlit
* **Vector DB**: FAISS
* **Embeddings**: HuggingFace
* **Database**: SQLite
* **APIs**: Alpha Vantage, DuckDuckGo

---

## 🚀 What This Demonstrates

This project showcases:

* ✅ Agent-based system design
* ✅ Tool orchestration logic
* ✅ RAG implementation
* ✅ Safe AI with human control
* ✅ Persistent conversational systems

👉 These are **core skills for real-world AI engineering roles**

---

## 🔮 Future Improvements

* 🌐 Deploy on Streamlit Cloud / AWS
* 🔐 Add authentication system
* 🧠 Multi-agent collaboration
* 📊 Portfolio tracking dashboard
* 🗂️ Multi-document retrieval

---

## 👨‍💻 Author

**Shubham Kumar**
GitHub: https://github.com/Shubham-kumar1-hub

---

## ⭐ Support

If you found this project useful:

⭐ Star the repo
🍴 Fork it
📢 Share it

---

