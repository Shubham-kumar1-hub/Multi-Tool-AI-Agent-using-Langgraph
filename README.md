# 🤖 Multi-Utility LangGraph Agent

A powerful **AI Agent built with LangGraph + LangChain + Streamlit** that supports:

* 📄 PDF-based Question Answering (RAG)
* 📈 Real-time Stock Data
* 🧮 Calculator
* 🌐 Web Search
* 🧑‍💻 Human-in-the-Loop (HITL) approvals
* 💬 Multi-threaded conversations with persistence

---

## 🚀 Features

### 🧠 Intelligent Agent (LangGraph)

* Graph-based execution using **StateGraph**
* Tool-calling LLM (Groq - LLaMA 3.3)
* Stateful conversations with checkpointing

### 📄 PDF RAG System

* Upload PDFs per chat thread
* Chunking + embeddings using HuggingFace
* FAISS vector store with disk persistence
* Context-aware answers with citations

### 🛠️ Built-in Tools

* 🔎 DuckDuckGo Search
* 📊 Stock Price Fetching (Alpha Vantage API)
* 🧮 Calculator (add, sub, mul, div)
* 💼 Buy/Sell Stocks (with approval)
* 📚 RAG Tool for document Q&A

### ⏸️ Human-in-the-Loop (HITL)

* Required approval before:

  * Buying stocks
  * Selling stocks
* Uses LangGraph `interrupt()` mechanism

### 💬 Streamlit Chat UI

* Multi-chat threads
* Persistent conversations (SQLite)
* Real-time streaming responses
* Tool execution visualization
* Sidebar PDF upload per thread

---

## 📁 Project Structure

```
.
├── Agent_backend.py      # Core LangGraph agent + tools + RAG
├── Agent_frontend.py     # Streamlit UI
├── requirements.txt      # Dependencies
├── .gitignore
└── faiss_indexes/        # Stored vector indexes (auto-created)
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/Shubham-kumar1-hub/Agent-using-Langgraph.git
cd Agent-using-Langgraph
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file:

```env
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

⚠️ Required for stock price tool.

---

## ▶️ Run the Application

```bash
streamlit run Agent_frontend.py
```

---

## 🧠 How It Works

### 🔹 1. LangGraph Workflow

The agent is built using a **StateGraph**:

```
START → chat_node → (tools if needed) → chat_node → END
```

* `chat_node` → LLM reasoning
* `tools` → executes selected tools
* Conditional routing using `tools_condition`

---

### 🔹 2. State Management

```python
class ChatState(TypedDict):
    messages
    thread_id
    uploaded_filename
    tool_call_count
```

* Prevents infinite loops
* Maintains conversation context

---

### 🔹 3. RAG Pipeline

* PDF uploaded via Streamlit
* Process:

  * Load → Split → Clean → Embed → Store (FAISS)
* Retrieval:

  * MMR-based search (`k=4`)
  * Returns page references

📌 Implemented in: 

---

### 🔹 4. Human-in-the-Loop (HITL)

Certain tools pause execution:

```python
decision = interrupt("Approve buying stocks?")
```

Frontend detects this and shows:

* ✅ Approve
* ❌ Cancel

Handled in: 

---

### 🔹 5. Persistent Memory

* SQLite checkpointing via LangGraph
* Conversations survive restarts
* Thread-based chat system

---

## 🛠️ Available Tools

| Tool                | Description           |
| ------------------- | --------------------- |
| `rag_tool`          | Query uploaded PDFs   |
| `get_stock_price`   | Fetch live stock data |
| `purchase_stock`    | Buy stocks (HITL)     |
| `sell_stock`        | Sell stocks (HITL)    |
| `calculator`        | Arithmetic operations |
| `duckduckgo_search` | Web search            |

---

## 💬 UI Features (Streamlit)

* Chat interface with streaming responses
* Sidebar:

  * Thread switching
  * PDF upload
  * Chat history
* Tool execution status indicators
* HITL approval banner

---

## 🔄 Example Flow

1. User uploads PDF
2. Asks question → RAG tool triggered
3. Agent retrieves relevant chunks
4. Response generated with context

OR

1. User asks: *“Buy 10 shares of AAPL”*
2. Agent triggers `purchase_stock`
3. UI asks for approval
4. Execution resumes based on decision

---

## 📦 Dependencies

See full list here: 

Key libraries:

* LangGraph
* LangChain
* Streamlit
* FAISS
* HuggingFace Embeddings
* Groq LLM

---

## 📌 Use Cases

* AI financial assistant
* Document QA system
* Tool-using autonomous agents
* Multi-step reasoning workflows
* Interactive AI dashboards

---

## 🔮 Future Improvements

* Add authentication
* Deploy on cloud (Streamlit Cloud / AWS)
* Add more tools (SQL, APIs)
* Multi-agent collaboration
* Voice input/output

---

## 👨‍💻 Author

**Shubham Kumar**
GitHub: https://github.com/Shubham-kumar1-hub

---

## ⭐ Support

If you found this useful, consider giving it a ⭐ on GitHub!
