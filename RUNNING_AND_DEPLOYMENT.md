# 🚀 Running & Deployment Guide

## 💻 Local Development (Run Now)

Follow these steps to run the **PeopleHub AI Assistant** locally on your machine.

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Setup Environment
Create a `.env` file in the root directory if you haven't already:
```bash
# .env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
LLAMA_CLOUD_API_KEY=llx-... (Optional, for better PDF parsing)
DATABASE_URL=sqlite:///data/hr_database.db
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
You need to run **two** separate terminals:

**Terminal 1: The Backend (FastAPI)**
This powers the API, Agent, and Database logic.
```bash
# Run from project root
uvicorn app.main:app --reload --port 8000
```
*Wait until you see "Application startup complete".*

**Terminal 2: The Frontend (Streamlit)**
This runs the chat interface.
```bash
# Run from project root
streamlit run streamlit_app.py
```
*The app should automatically open in your browser (usually http://localhost:8501).*

---

## 🌍 Production Deployment (Roadmap)

Moving from this MVP to a real production environment requires several upgrades.

### 1. Containerization (Docker)
Instead of running two terminals, containerize the app:
*   Create a `Dockerfile` for the FastAPI backend.
*   Create a `Dockerfile` for the Streamlit frontend.
*   Use `docker-compose.yml` to orchestrate them together.

### 2. Database Migration
*   **Current:** SQLite (File-based, good for testing).
*   **Production:** PostgreSQL (Hosted on Supabase, AWS RDS, or Azure).
    *   Update `DATABASE_URL` env var.
    *   Use `alembic` for database migrations (schema changes).

### 3. Security
*   **Authentication:** Replace the "Select Employee" sidebar with real OAuth2 / SSO (Single Sign-On).
*   **HTTPS:** Serve the app over HTTPS using a reverse proxy (Nginx) or a cloud load balancer.
*   **Secrets:** Function calls (Tool use) should be carefully scoped. Ensure the API keys for tools have minimum required permissions.

### 4. Server
*   **Backend:** Use a production-grade server like `gunicorn` with `uvicorn` workers.
    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
    ```
*   **Frontend:** Host Streamlit on Streamlit Cloud or within the same Docker network.

### 5. Vector Store
*   **Current:** ChromaDB (Local persistence).
*   **Production:** ChromaDB Server mode or a managed vector provider (Pinecone, Weaviate) to handle concurrency and scaling.
