"""Configuration management for Solvait AI Assistant."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MANUALS_DIR = DATA_DIR / "manuals"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MANUALS_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/hr_database.db")

# API Base URL for payslip downloads and other resources
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Model settings
EMBEDDING_MODEL = "models/embedding-001"
LLM_MODEL = "gemini-2.0-flash"

# Debug/Trace mode - set to True to see RAG chunks, tool calls, reasoning
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() in ("true", "1", "yes")
