# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Solvait AI Assistant is an intelligent HR AI agent built with LlamaIndex and Gemini. It provides a conversational interface for employees to check leave balances, submit requests, view payslips, create tickets, and ask HR policy questions. The system supports bilingual interactions (Arabic/English).

## Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend (Terminal 1)
uvicorn app.main:app --reload --port 8000

# Start Streamlit frontend (Terminal 2)
streamlit run streamlit_app.py
```

### Environment Setup

Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY` - for embeddings
- `GOOGLE_API_KEY` - for Gemini LLM
- `LLAMA_CLOUD_API_KEY` - optional, for LlamaParse

### API Docs

FastAPI auto-generates docs at `http://localhost:8000/docs`

## Architecture

```
Streamlit UI (streamlit_app.py)
    │
    ▼ HTTP
FastAPI Backend (app/main.py)
    │
    ▼
LlamaIndex ReActAgent (app/agent/hr_agent.py)
    │
    ├──► RAG System (app/rag/) ──► ChromaDB (data/chroma_db/)
    │       └── PolicyEngine: queries HR policy documents
    │
    └──► MCP Tools (app/mcp/) ──► SQLite (data/hr_database.db)
            └── HRService: CRUD operations for leave, payslips, tickets
```

### Key Components

- **`app/main.py`**: FastAPI entrypoint with `/chat`, `/health`, `/ingest`, `/employees` endpoints
- **`app/agent/hr_agent.py`**: HRAgent class wrapping LlamaIndex ReActAgent with singleton pattern (`get_hr_agent()`)
- **`app/agent/prompts.py`**: Bilingual system prompts with pre-action validation protocols
- **`app/mcp/tools.py`**: 8 FunctionTools (5 read, 3 write) for HR operations
- **`app/mcp/hr_service.py`**: Business logic layer with validation and Arabic translations
- **`app/rag/policy_engine.py`**: RAG query engine for HR policies, wrapped as QueryEngineTool
- **`app/rag/ingestion.py`**: PDF parsing (LlamaParse/PyMuPDF fallback) and ChromaDB indexing
- **`app/db/models.py`**: SQLAlchemy models (Employee, LeaveBalance, LeaveRequest, Payslip, Excuse, Ticket)
- **`app/db/seed.py`**: Mock data seeder for development

### Pre-Action Protocol

The agent enforces a validation protocol before submitting leave requests:
1. Call `get_leave_balance` to verify sufficient balance
2. Call `get_team_calendar` to check for team conflicts
3. Inform user of conflicts and get explicit confirmation
4. Only then call `submit_leave_request`

This protocol is defined in `app/agent/prompts.py` and documented in `app/mcp/tools.py`.

### Bilingual Support

- Language detection uses Unicode range check for Arabic characters
- System prompts in `prompts.py` are bilingual (Arabic + English)
- HRService includes Arabic translations for leave types and statuses
- Streamlit UI applies RTL styling for Arabic responses

## Data

- **Policy documents**: Place PDFs in `data/manuals/`, call `POST /ingest` to reindex
- **Vector store**: ChromaDB persists to `data/chroma_db/`
- **Database**: SQLite at `data/hr_database.db` (development)
