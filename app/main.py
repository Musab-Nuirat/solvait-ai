"""FastAPI Application - Solvait AI Assistant API."""

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
    import asyncio
    import sys

    # Fix encoding for Windows console
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    # Startup
    print("[START] Starting Solvait AI Assistant...")

    # Initialize SQLite database
    init_db()
    seed_database()
    print("[OK] SQLite database ready")

    # Initialize ChromaDB and ingest documents (creates vectors on fresh deploy)
    print("[LOAD] Initializing RAG system...")
    from app.rag.policy_engine import get_policy_engine
    policy_engine = get_policy_engine()
    print("[OK] ChromaDB ready with policy documents")

    # Yield control to the application
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        # Normal shutdown - these errors are expected during Ctrl+C
        pass
    finally:
        # Shutdown cleanup
        try:
            print("[STOP] Shutting down gracefully...")
            # Add any cleanup logic here if needed (e.g., close database connections)
        except Exception:
            # Suppress any errors during shutdown
            pass


# ============================================
# APPLICATION
# ============================================

app = FastAPI(
    title="Solvait AI Assistant",
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
        "service": "Solvait AI Assistant",
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


@app.get("/database")
async def get_database():
    """Get all database tables for frontend display."""
    from app.db.database import get_db_session
    from app.db.models import Employee, LeaveBalance, LeaveRequest, Ticket, Payslip, Excuse

    with get_db_session() as db:
        # Employees
        employees = db.query(Employee).all()
        employees_data = [
            {"ID": e.id, "Name": e.name, "Dept": e.department, "Title": e.title}
            for e in employees
        ]

        # Leave balances
        balances = db.query(LeaveBalance).all()
        balances_data = [
            {"Employee": b.employee_id, "Type": b.leave_type.value, "Days": b.balance_days}
            for b in balances
        ]

        # Leave requests
        requests = db.query(LeaveRequest).all()
        requests_data = [
            {
                "ID": r.id,
                "Employee": r.employee_id,
                "Type": r.leave_type.value,
                "From": str(r.start_date),
                "To": str(r.end_date),
                "Status": r.status.value
            }
            for r in requests
        ]

        # Tickets
        tickets = db.query(Ticket).all()
        tickets_data = [
            {
                "ID": f"TK-{t.id:04d}",
                "Employee": t.employee_id,
                "Category": t.category,
                "Status": t.status.value
            }
            for t in tickets
        ]

        # Helper to safely get attribute with default
        def safe_get(obj, attr, default=0):
            return getattr(obj, attr, default) or default

        return {
            "employees": employees_data,
            "leave_balances": balances_data,
            "leave_requests": requests_data,
            "tickets": tickets_data,
            # Detailed payslips view
            "payslips": [
                {
                    "ID": str(p.id),
                    "Employee": p.employee_id,
                    "Period": f"{p.year}-{str(p.month).zfill(2)}",
                    "Basic": p.basic_salary,
                    "Housing": safe_get(p, 'housing_allowance'),
                    "Transport": safe_get(p, 'transport_allowance'),
                    "Phone": safe_get(p, 'phone_allowance'),
                    "Meal": safe_get(p, 'meal_allowance'),
                    "Other Allow": safe_get(p, 'other_allowances'),
                    "GOSI": safe_get(p, 'gosi_deduction'),
                    "Tax": safe_get(p, 'tax_deduction'),
                    "Loan": safe_get(p, 'loan_deduction'),
                    "Net Salary": p.net_salary
                } for p in db.query(Payslip).all()
            ],
            "excuses": [
                {
                    "ID": str(e.id),
                    "Employee": e.employee_id,
                    "Date": str(e.date),
                    "Type": e.excuse_type.value,
                    "Time": str(e.start_time or e.end_time),
                    "Reason": e.reason,
                    "Status": e.status.value
                } for e in db.query(Excuse).all()
            ]
        }


@app.post("/reset-db")
async def reset_database():
    """Clear and reseed the database."""
    from app.db.database import SessionLocal, engine
    from app.db.models import Base
    import time

    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Small delay to ensure tables are fully created
    time.sleep(0.1)

    # Reseed with force=True to ensure it always seeds
    seed_database(force=True)

    return {"status": "success", "message": "Database reset and reseeded"}


# ============================================
# RUN (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn
    import sys
    import warnings
    
    # Suppress asyncio CancelledError warnings during shutdown
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*CancelledError.*")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down server gracefully...")
        sys.exit(0)
