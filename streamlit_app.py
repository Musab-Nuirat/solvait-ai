"""Streamlit Chat UI for Solvait AI Assistant."""

import os
import streamlit as st
import requests
from typing import Optional, Tuple

# ============================================
# CONFIGURATION
# ============================================

# API URL: Use environment variable for production, fallback to localhost for dev
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Solvait AI Assistant",
    page_icon="🧑‍💼",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS for RTL Arabic Support
# ============================================

st.markdown("""
<style>
/* RTL support for Arabic messages */
.rtl-text {
    direction: rtl;
    text-align: right;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Chat message styling */
.stChatMessage {
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
}

/* User message styling */
[data-testid="stChatMessageContent"] {
    font-size: 1rem;
    line-height: 1.6;
}

/* Trace box styling */
.trace-box {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.8rem;
    overflow-x: auto;
    margin-top: 0.5rem;
}

.trace-query { color: #569cd6; }
.trace-retrieval { color: #4ec9b0; }
.trace-chunks { color: #dcdcaa; }
.trace-tool { color: #c586c0; }
.trace-llm { color: #ce9178; }
.trace-response { color: #6a9955; }
.trace-error { color: #f44747; }
.trace-time { color: #808080; }

/* Header styling */
.main-header {
    text-align: center;
    padding: 1rem 0 2rem 0;
}

/* Employee selector card */
.employee-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}

/* Chunk card styling */
.chunk-card {
    background-color: #f8f9fa;
    border-left: 3px solid #667eea;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 0 8px 8px 0;
    font-size: 0.85rem;
}
.chunk-header {
    color: #667eea;
    font-weight: bold;
    font-size: 0.75rem;
    margin-bottom: 0.25rem;
}
.chunk-text {
    color: #333;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأإؤئ')
    return any(char in arabic_chars for char in text)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_employees():
    """Fetch employee list from API."""
    try:
        response = requests.get(f"{API_URL}/employees", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    # Fallback mock data if API unavailable
    return [
        {"id": "EMP001", "name": "Ahmed Al-Rashid", "name_ar": "أحمد الراشد", "department": "Engineering"},
        {"id": "EMP002", "name": "Khalid Ibrahim", "name_ar": "خالد إبراهيم", "department": "Engineering"},
        {"id": "EMP003", "name": "Sara Mohammed", "name_ar": "سارة محمد", "department": "Engineering"},
    ]


def send_message(
    user_id: str,
    message: str,
    chat_history: list = None,
    include_traces: bool = False
) -> Tuple[Optional[str], list]:
    """Send message to the API and get response with optional traces."""
    try:
        # Convert chat history to API format (exclude traces)
        history_for_api = []
        if chat_history:
            for msg in chat_history:
                history_for_api.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        response = requests.post(
            f"{API_URL}/chat",
            json={
                "user_id": user_id,
                "message": message,
                "chat_history": history_for_api,
                "include_traces": include_traces
            },
            timeout=120  # LLM can take time
        )
        if response.status_code == 200:
            data = response.json()
            return data["response"], data.get("traces", [])
        else:
            return f"Error: {response.status_code}", []
    except requests.exceptions.ConnectionError:
        return "Cannot connect to server. Make sure FastAPI is running.", []
    except Exception as e:
        return f"Error: {str(e)}", []


def render_traces(traces: list):
    """Render debug traces in a formatted view."""
    if not traces:
        return

    with st.expander("🔍 Debug Traces (RAG Process)", expanded=False):
        # Summary stats
        col1, col2, col3 = st.columns(3)
        chunk_traces = [t for t in traces if t.get("category") == "CHUNKS"]
        tool_traces = [t for t in traces if t.get("category") == "TOOL_CALL"]
        total_time = traces[-1].get("elapsed_ms", 0) if traces else 0

        with col1:
            st.metric("Total Time", f"{total_time}ms")
        with col2:
            st.metric("Chunks Retrieved", sum(len(t.get("data", [])) for t in chunk_traces))
        with col3:
            st.metric("Tool Calls", len(tool_traces))

        st.divider()

        # Detailed traces
        for trace in traces:
            category = trace.get("category", "INFO")
            elapsed = trace.get("elapsed_ms", 0)
            message = trace.get("message", "")
            data = trace.get("data")

            # Category colors
            color_map = {
                "QUERY": "trace-query",
                "RETRIEVAL": "trace-retrieval",
                "CHUNKS": "trace-chunks",
                "TOOL_CALL": "trace-tool",
                "TOOL_RESULT": "trace-tool",
                "LLM": "trace-llm",
                "RESPONSE": "trace-response",
                "ERROR": "trace-error",
            }
            css_class = color_map.get(category, "")

            # Render trace entry
            st.markdown(
                f'<div class="trace-box">'
                f'<span class="trace-time">[{elapsed:>5}ms]</span> '
                f'<span class="{css_class}">[{category}]</span> {message}'
                f'</div>',
                unsafe_allow_html=True
            )

            # Render chunk details
            if category == "CHUNKS" and data:
                for chunk in data:
                    score = chunk.get("score", 0)
                    source = chunk.get("source", "unknown")
                    text = chunk.get("text", "")
                    st.markdown(
                        f'<div class="chunk-card">'
                        f'<div class="chunk-header">📄 {source} | Score: {score:.4f}</div>'
                        f'<div class="chunk-text">{text}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )


# ============================================
# SIDEBAR - Employee Selection & Settings
# ============================================

with st.sidebar:
    st.markdown("## 👤 Select Employee")

    employees = get_employees()

    # Create dropdown options
    emp_options = {f"{e['name_ar']} ({e['id']})": e['id'] for e in employees}

    selected_display = st.selectbox(
        "Choose employee:",
        options=list(emp_options.keys()),
        index=0
    )

    selected_employee_id = emp_options[selected_display]

    # Show selected employee info
    selected_emp = next((e for e in employees if e['id'] == selected_employee_id), None)
    if selected_emp:
        st.markdown(f"""
        <div class="employee-card">
            <strong>{selected_emp['name_ar']}</strong><br>
            <small>{selected_emp['name']}</small><br>
            <small>📍 {selected_emp['department']}</small>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Debug mode toggle
    st.markdown("### ⚙️ Settings")
    debug_mode = st.toggle("🔍 Show Debug Traces", value=False, help="Show RAG chunks, tool calls, and timing")

    st.divider()

    # Quick actions
    st.markdown("### ⚡ Quick Actions")

    if st.button("📊 Check Leave Balance", width='stretch'):
        st.session_state.quick_message = "كم رصيد إجازاتي؟"

    if st.button("💰 View Payslip", width='stretch'):
        st.session_state.quick_message = "أريد رؤية قسيمة راتبي"

    if st.button("📋 Request Leave", width='stretch'):
        st.session_state.quick_message = "أريد طلب إجازة يوم الاثنين القادم"

    if st.button("📖 Policy Question", width='stretch'):
        st.session_state.quick_message = "What is the overtime policy?"

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear Chat", width='stretch'):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # ============================================
    # DATABASE VIEWER
    # ============================================
    st.markdown("### 🗄️ Database")

    # Refresh database view button (just refreshes the display, doesn't reset data)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh View", width='stretch', help="Refresh the database view without resetting data"):
            # Clear cache to ensure fresh data is fetched
            st.cache_data.clear()
            st.success("View refreshed!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Reset Database", width='stretch', help="⚠️ WARNING: This will delete all data and reset to initial state"):
            try:
                # Clear and reseed database
                with st.spinner("Resetting database to initial state..."):
                    response = requests.post(f"{API_URL}/reset-db", timeout=30)
                    if response.status_code == 200:
                        st.success("Database reset to initial state!")
                        # Clear cache to ensure fresh data
                        st.cache_data.clear()
                        # Small delay to ensure database is fully committed
                        import time
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("Server not running")
            except Exception as e:
                st.error(f"Error resetting database: {str(e)}")

    # Fetch database tables
    @st.cache_data(ttl=1)  # Cache for 1 second to avoid rapid refetches
    def get_db_tables():
        """Fetch all database tables from API."""
        try:
            response = requests.get(f"{API_URL}/database", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Error fetching database: {str(e)}")
        return None

    db_data = get_db_tables()

    if db_data:
        with st.expander("👥 Employees"):
            if db_data.get("employees"):
                st.dataframe(db_data["employees"], width='stretch', hide_index=True)
            else:
                st.info("No employees")

        with st.expander("📅 Leave Requests"):
            if db_data.get("leave_requests"):
                st.dataframe(db_data["leave_requests"], width='stretch', hide_index=True)
            else:
                st.info("No leave requests")

        with st.expander("💰 Leave Balances"):
            if db_data.get("leave_balances"):
                st.dataframe(db_data["leave_balances"], width='stretch', hide_index=True)
            else:
                st.info("No balances")

        with st.expander("🎫 Tickets"):
            if db_data.get("tickets"):
                st.dataframe(db_data["tickets"], width='stretch', hide_index=True)
            else:
                st.info("No tickets")

        with st.expander("💸 Payslips"):
            if db_data.get("payslips"):
                st.dataframe(db_data["payslips"], width='stretch', hide_index=True)
            else:
                st.info("No payslips")

        with st.expander("⏳ Excuses"):
            if db_data.get("excuses"):
                st.dataframe(db_data["excuses"], width='stretch', hide_index=True)
            else:
                st.info("No excuses")


# ============================================
# MAIN CHAT INTERFACE
# ============================================

# Header
st.markdown("""
<div class="main-header">
    <h1>🧑‍💼 Solvait AI Assistant</h1>
    <p style="color: #666;">مساعدك الذكي للموارد البشرية | Your Intelligent HR Assistant</p>
</div>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Welcome message
    welcome_msg = """
مرحباً! 👋 أنا مساعد Solvait الذكي.

يمكنني مساعدتك في:
- ✅ الاستفسار عن رصيد الإجازات
- ✅ طلب إجازة جديدة
- ✅ عرض قسيمة الراتب
- ✅ تسجيل استئذان (تأخر/مغادرة مبكرة)
- ✅ الإجابة على أسئلة سياسات الشركة

كيف يمكنني مساعدتك اليوم؟

---

Hello! 👋 I'm Solvait AI Assistant.

I can help you with:
- ✅ Check leave balances
- ✅ Submit leave requests
- ✅ View payslips
- ✅ Create excuse requests
- ✅ Answer policy questions

How can I help you today?
"""
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg, "traces": []})

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        content = message["content"]

        # Apply RTL styling for Arabic content
        if is_arabic(content):
            st.markdown(f'<div class="rtl-text">{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(content)

        # Show traces if available and debug mode is on
        if debug_mode and message.get("traces"):
            render_traces(message["traces"])

# Handle quick action messages
if "quick_message" in st.session_state:
    quick_msg = st.session_state.pop("quick_message")
    st.session_state.messages.append({"role": "user", "content": quick_msg, "traces": []})

    with st.chat_message("user"):
        st.markdown(f'<div class="rtl-text">{quick_msg}</div>', unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner("🤔 جاري التفكير... / Thinking..."):
            # Pass chat history for context
            response, traces = send_message(
                selected_employee_id,
                quick_msg,
                chat_history=st.session_state.messages[:-1],  # Exclude the just-added user message
                include_traces=debug_mode
            )

        if is_arabic(response):
            st.markdown(f'<div class="rtl-text">{response}</div>', unsafe_allow_html=True)
        else:
            st.markdown(response)

        if debug_mode and traces:
            render_traces(traces)

    st.session_state.messages.append({"role": "assistant", "content": response, "traces": traces})
    st.rerun()

# Chat input
if prompt := st.chat_input("اكتب رسالتك هنا... / Type your message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt, "traces": []})

    with st.chat_message("user"):
        if is_arabic(prompt):
            st.markdown(f'<div class="rtl-text">{prompt}</div>', unsafe_allow_html=True)
        else:
            st.markdown(prompt)

    # Get and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤔 جاري التفكير... / Thinking..."):
            # Pass chat history for context
            response, traces = send_message(
                selected_employee_id,
                prompt,
                chat_history=st.session_state.messages[:-1],  # Exclude the just-added user message
                include_traces=debug_mode
            )

        if is_arabic(response):
            st.markdown(f'<div class="rtl-text">{response}</div>', unsafe_allow_html=True)
        else:
            st.markdown(response)

        if debug_mode and traces:
            render_traces(traces)

    st.session_state.messages.append({"role": "assistant", "content": response, "traces": traces})


# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.markdown(
    "<center><small>Solvait AI Assistant v0.1.0</small></center>",
    unsafe_allow_html=True
)
