# Solvait AI Assistant - POC

An intelligent HR AI Agent built with LlamaIndex, supporting bilingual (Arabic/English) interactions.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy template
copy .env.example .env

# Edit .env and add your keys:
# - OPENAI_API_KEY (for embeddings)
# - GOOGLE_API_KEY (for Gemini LLM)
# - LLAMA_CLOUD_API_KEY (optional, for LlamaParse)
```

### 3. Run the Application

**Terminal 1 - Start FastAPI Backend:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Start Streamlit UI:**
```bash
streamlit run streamlit_app.py
```

### 4. Open in Browser

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs

---

## 📁 Project Structure

```
solvait/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Environment config
│   ├── agent/
│   │   ├── hr_agent.py      # LlamaIndex ReActAgent
│   │   └── prompts.py       # Bilingual system prompts
│   ├── rag/
│   │   ├── ingestion.py     # LlamaParse + MarkdownNodeParser
│   │   └── policy_engine.py # RAG query engine
│   ├── mcp/
│   │   ├── tools.py         # 8 MCP tool definitions
│   │   └── hr_service.py    # Business logic layer
│   └── db/
│       ├── models.py        # SQLAlchemy models
│       ├── database.py      # DB connection
│       └── seed.py          # Mock data seeder
├── data/
│   ├── manuals/             # Put PDF manuals here
│   └── chroma_db/           # Vector store
├── streamlit_app.py         # Chat UI
├── requirements.txt
└── .env.example
```

---

## 🧪 Demo Scenarios

### 1. Conflict Detection
```
User: "أريد إجازة يوم الاثنين القادم"
AI: "زميلك خالد إبراهيم لديه إجازة موافق عليها في هذا التاريخ. هل تريد الاستمرار؟"
```

### 2. Insufficient Balance
```
User (as Omar): "I want to take 5 days annual leave"
AI: "You only have 2 days annual leave remaining. Would you like to use Unpaid Leave?"
```

### 3. Policy Questions
```
User: "Is dental coverage included?"
AI: "Yes, according to Section 4.1 of the Employee Handbook, dental coverage is included in the standard plan."
```

---

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/chat` | POST | Chat with AI agent |
| `/employees` | GET | List all employees |
| `/ingest` | POST | Re-ingest policy documents |

---

## 📄 Adding Policy Documents

1. Place PDF files in `data/manuals/`
2. Call `POST /ingest` with `force_reindex: true`
3. Or restart the server

---

## 🌐 Deployment (Render)

```yaml
# render.yaml
services:
  - type: web
    name: Solvait-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

Made with ❤️ using LlamaIndex + Gemini + FastAPI + Streamlit
