"""FastAPI Application - PeopleHub AI Assistant API."""

from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.db.seed import seed_database
from app.agent.hr_agent import get_hr_agent


# ============================================
# LIFESPAN - Startup/Shutdown Events
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print("🚀 Starting PeopleHub AI Assistant...")
    init_db()
    seed_database()
    print("✅ Database ready")
    yield
    # Shutdown
    print("👋 Shutting down...")


# ============================================
# APPLICATION
# ============================================

app = FastAPI(
    title="PeopleHub AI Assistant",
    description="Intelligent HR Agent with RAG capabilities",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# SCHEMAS
# ============================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    user_id: str = "EMP001"  # Default to Ahmed for demo
    message: str
    chat_history: list[ChatMessage] = []  # Previous messages for context
    include_traces: bool = False  # Set to True to get debug traces


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    user_id: str
    message: str
    response: str
    traces: list = []  # Debug traces (when include_traces=True)


class IngestRequest(BaseModel):
    """Request body for document ingestion."""
    force_reindex: bool = False


# ============================================
# ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PeopleHub AI Assistant",
        "version": "0.1.0"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the HR AI Assistant.

    The agent will:
    1. Detect the language (Arabic/English)
    2. Search policies if needed
    3. Check/execute HR operations
    4. Respond in the user's language

    Set include_traces=True to get debug information about RAG chunks, tool calls, etc.
    Pass chat_history to maintain conversation context.
    """
    try:
        # Get agent for this user
        agent = get_hr_agent(request.user_id)

        # Convert chat history to list of dicts
        history = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]

        # Process message using async method with history
        result = await agent.chat_async(
            request.message,
            chat_history=history,
            return_traces=request.include_traces
        )

        return ChatResponse(
            user_id=request.user_id,
            message=request.message,
            response=result["response"],
            traces=result.get("traces", [])
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_documents(request: IngestRequest):
    """
    Trigger re-ingestion of policy documents.
    
    Use force_reindex=true to rebuild the entire index.
    """
    try:
        from app.rag.ingestion import DocumentIngestion
        ingestion = DocumentIngestion()
        index = ingestion.ingest_manuals(force_reindex=request.force_reindex)
        
        return {
            "status": "success",
            "message": "Documents ingested successfully",
            "force_reindex": request.force_reindex
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/employees")
async def list_employees():
    """List all employees (for UI dropdown)."""
    from app.db.database import get_db_session
    from app.db.models import Employee
    
    with get_db_session() as db:
        employees = db.query(Employee).all()
        return [
            {
                "id": e.id,
                "name": e.name,
                "name_ar": e.name_ar,
                "department": e.department,
                "title": e.title
            }
            for e in employees
        ]


# ============================================
# RUN (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
