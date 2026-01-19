# Solvait AI Assistant - Codebase Overview

This document provides a high-level overview of the Solvait AI Assistant codebase, explaining its architecture, components, and how they work together.

## Project Overview

The Solvait AI Assistant is a bilingual (Arabic/English) AI-powered HR assistant. It's a proof-of-concept that combines a FastAPI backend with a Streamlit frontend. The assistant can answer questions about company policies, manage leave requests, and perform other HR-related tasks.

## Architecture

The application is built with a client-server architecture:

*   **Frontend (Client):** A Streamlit web application that provides the user interface for interacting with the AI assistant.
*   **Backend (Server):** A FastAPI application that exposes a REST API. The backend handles the core business logic, including the AI agent, RAG system, and database interactions.

## Core Technologies

*   **Backend:** FastAPI
*   **Frontend:** Streamlit
*   **AI/LLM:** LlamaIndex, Google Gemini
*   **Database:** SQLAlchemy with SQLite
*   **Vector Store:** ChromaDB for the RAG system
*   **Deployment:** Configured for Render

## Project Structure

Here's a breakdown of the most important files and directories:

```
solvait/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment variable configuration
│   ├── agent/
│   │   ├── hr_agent.py      # The core LlamaIndex ReActAgent
│   │   └── prompts.py       # System prompts for the AI agent
│   ├── rag/
│   │   ├── ingestion.py     # Logic for ingesting policy documents
│   │   └── policy_engine.py # The RAG query engine
│   ├── mcp/
│   │   ├── tools.py         # Defines the tools the agent can use
│   │   └── hr_service.py    # Business logic for HR operations
│   └── db/
│       ├── models.py        # SQLAlchemy database models
│       ├── database.py      # Database connection and session management
│       └── seed.py          # Script to seed the database with initial data
├── data/
│   ├── manuals/             # PDF policy documents are stored here
│   └── chroma_db/           # The ChromaDB vector store
├── streamlit_app.py         # The Streamlit frontend application
├── requirements.txt         # Python dependencies
├── README.md                # Project README
└── CODEBASE_OVERVIEW.md     # This file
```

## How it Works

1.  **User Interaction:** The user interacts with the chat interface in the Streamlit application (`streamlit_app.py`).
2.  **API Request:** The Streamlit app sends the user's message to the FastAPI backend (`app/main.py`) via an HTTP request.
3.  **Agent Processing:** The FastAPI backend passes the message to the HR agent (`app/agent/hr_agent.py`).
4.  **Intent Detection:** The agent, powered by LlamaIndex and Google Gemini, analyzes the message to understand the user's intent.
5.  **Tool Usage/RAG:**
    *   If the user asks a question about company policy, the agent uses the RAG system (`app/rag/policy_engine.py`) to retrieve relevant information from the policy documents.
    *   If the user wants to perform an HR action (e.g., request leave), the agent uses one of the tools defined in `app/mcp/tools.py` to interact with the database.
6.  **Response Generation:** The agent generates a response in the user's language (Arabic or English).
7.  **API Response:** The FastAPI backend sends the agent's response back to the Streamlit frontend.
8.  **Display to User:** The Streamlit app displays the response to the user.

## Key Components

### FastAPI Backend (`app/`)

*   **`main.py`:** The heart of the backend. It defines all the API endpoints, manages the application's lifecycle (startup and shutdown), and integrates all the other backend components.
*   **`agent/hr_agent.py`:** This is where the LlamaIndex `ReActAgent` is configured. The agent is responsible for orchestrating the entire process of understanding the user's query, using the available tools, and generating a response.
*   **`rag/policy_engine.py`:** This component is responsible for the Retrieval-Augmented Generation (RAG) functionality. It uses ChromaDB to store and query vector embeddings of the policy documents.
*   **`mcp/tools.py`:** This file defines the functions that the AI agent can call to perform actions, such as `get_leave_balance` or `submit_leave_request`. These tools are the bridge between the AI agent and the application's business logic.
*   **`db/`:** This directory manages all database-related functionality. `models.py` defines the database schema, `database.py` handles the connection, and `seed.py` populates the database with initial data.

### Streamlit Frontend (`streamlit_app.py`)

This single file contains the entire user interface. It's responsible for:

*   Displaying the chat interface.
*   Allowing the user to select an employee.
*   Sending user messages to the backend API.
*   Displaying the AI assistant's responses.
*   Providing a view of the data in the database tables.
