"""MCP Tools for LlamaIndex Agent - HR Operations."""

from datetime import date, datetime
from typing import Optional
from llama_index.core.tools import FunctionTool

from app.db.database import get_db_session
from app.mcp.hr_service import HRService


# ============================================
# READ TOOLS
# ============================================

def get_employee_profile(employee_id: str) -> str:
    """
    Get the profile information of an employee.
    
    Args:
        employee_id: The employee ID (e.g., "EMP001")
    
    Returns:
        Employee profile including name, department, title, hire date, and tenure.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_employee_profile(employee_id)
        return str(result)


def get_leave_balance(employee_id: str, leave_type: Optional[str] = None) -> str:
    """
    Get the leave balance for an employee.
    
    Args:
        employee_id: The employee ID (e.g., "EMP001")
        leave_type: Optional. Type of leave: "annual", "sick", or "unpaid". 
                   If not specified, returns all leave types.
    
    Returns:
        Leave balance information showing remaining days for each leave type.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_leave_balance(employee_id, leave_type)
        return str(result)


def get_team_members(department: str) -> str:
    """
    Get all team members in a specific department.
    Use this to find out who is on your team before checking calendars.

    Args:
        department: The department name (e.g., "Engineering", "HR", "Finance")

    Returns:
        List of team members with their names and titles.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_team_members(department)
        return str(result)


def get_team_calendar(department: str, start_date: str, end_date: str) -> str:
    """
    ⭐ IMPORTANT: Check team leave calendar BEFORE submitting any leave request.
    This helps detect conflicts with teammates who are already on leave.
    
    Args:
        department: The department name (e.g., "Engineering", "HR", "Finance")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of team members who have approved or pending leave during this period.
        If has_conflicts is True, warn the user before proceeding.
    """
    with get_db_session() as db:
        service = HRService(db)
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: Invalid date format. Please use YYYY-MM-DD."
            
        result = service.get_team_calendar(department, start, end)
        return str(result)


def get_payslip(employee_id: str, month: Optional[int] = None, year: Optional[int] = None) -> str:
    """
    Get the payslip for an employee.
    
    Args:
        employee_id: The employee ID (e.g., "EMP001")
        month: Optional. Month number (1-12). If not specified, returns latest payslip.
        year: Optional. Year (e.g., 2024). Required if month is specified.
    
    Returns:
        Payslip details including net salary, allowances breakdown, and deductions.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_payslip(employee_id, month, year)
        return str(result)


def get_ticket_status(ticket_id: int) -> str:
    """
    Get the status of a support ticket.
    
    Args:
        ticket_id: The ticket ID number
    
    Returns:
        Ticket details including category, description, and current status.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_ticket_status(ticket_id)
        return str(result)


# ============================================
# WRITE TOOLS
# ============================================

def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: Optional[str] = None,
    confirm_conflicts: bool = False,
    user_confirmed: bool = False
) -> str:
    """
    Submit a new leave request for an employee.

    ⚠️ CRITICAL: DO NOT call this tool until you have ALL required information from the user:
    - leave_type: The user MUST specify annual, sick, or unpaid
    - start_date: The user MUST provide the start date
    - end_date: The user MUST provide the end date

    If ANY of these are missing, ASK THE USER first. Do NOT invent or assume dates.

    🛑 MANDATORY CONFIRMATION WORKFLOW:
    1. Gather all info (leave_type, start_date, end_date)
    2. Call get_leave_balance to check current balance
    3. Show user a CONFIRMATION SUMMARY:
       "📋 Leave Request Summary:
        Type: [leave_type]
        From: [start_date]
        To: [end_date]
        Duration: [X days]
        Your balance: [current] → [remaining] days

        Do you want to submit this request? (Yes/No)"
    4. Wait for explicit "yes" / "نعم" / "تمام" / "confirm"
    5. ONLY THEN call this function with user_confirmed=True

    ⚠️ CONFLICT HANDLING:
    - First call with confirm_conflicts=False
    - If result contains "warning": "team_conflict":
       - Tell the user about the conflicting team members
       - Ask if they want to proceed anyway
    - Only if user confirms, call again with confirm_conflicts=True

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        leave_type: Type of leave: "annual", "sick", or "unpaid"
        start_date: Start date in YYYY-MM-DD format (MUST be provided by user, not invented!)
        end_date: End date in YYYY-MM-DD format (MUST be provided by user, not invented!)
        reason: Optional reason for the leave
        confirm_conflicts: Set to True ONLY after user confirms they want to proceed despite team conflicts
        user_confirmed: Set to True ONLY after user explicitly confirms the summary. Required!

    Returns:
        - If user_confirmed=False: Instructions to show confirmation summary
        - If conflicts exist and confirm_conflicts=False: Warning with conflict details
        - If no conflicts or confirm_conflicts=True: Success confirmation with request ID
        - Error if validation fails (insufficient balance, invalid dates, etc.)
    """
    # CRITICAL: Block if user hasn't confirmed (unless just checking for conflicts)
    if not user_confirmed and not confirm_conflicts:
        # Calculate duration for the summary
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            duration = (end - start).days + 1
        except ValueError:
            duration = "?"

        return f"""🛑 STOP! You must get user confirmation first!

Please show this summary to the user and ask for confirmation:

📋 **Leave Request Summary:**
┌────────────────────────────────┐
│ Type:       {leave_type.title()} Leave
│ From:       {start_date}
│ To:         {end_date}
│ Duration:   {duration} day(s)
└────────────────────────────────┘

⚠️ IMPORTANT: Also show the balance impact:
"You have X days of {leave_type} leave. This will use {duration} days, leaving you with Y days."

"Do you want to submit this request? (Yes/No)"
"هل تريد تقديم هذا الطلب؟ (نعم/لا)"

ONLY call submit_leave_request with user_confirmed=True after user says "yes" or "نعم".
"""
    with get_db_session() as db:
        service = HRService(db)
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: Invalid date format. Please use YYYY-MM-DD."

        # Validate dates are not in the past
        today = date.today()
        if start < today:
            return f"Error: Cannot submit leave for past dates. Start date {start_date} is before today ({today}). Please ask the user for correct future dates."
        if end < start:
            return f"Error: End date {end_date} cannot be before start date {start_date}. Please ask the user for correct dates."

        result = service.submit_leave_request(
            employee_id, leave_type, start, end, reason, confirm_conflicts
        )
        return str(result)


def check_duplicate_excuse(
    employee_id: str,
    excuse_date: str,
    excuse_type: str
) -> str:
    """
    Check if an excuse already exists for the same date and type.

    ⚠️ IMPORTANT: Call this BEFORE creating an excuse to prevent duplicates!

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        excuse_date: Date to check in YYYY-MM-DD format
        excuse_type: Type: "late_arrival" or "early_departure"

    Returns:
        Information about whether a duplicate exists.
    """
    with get_db_session() as db:
        service = HRService(db)
        try:
            exc_date = datetime.strptime(excuse_date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: Invalid date format. Please use YYYY-MM-DD."

        result = service.check_duplicate_excuse(employee_id, exc_date, excuse_type)
        return str(result)


def create_excuse(
    employee_id: str,
    excuse_date: str,
    excuse_type: str,
    reason: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user_confirmed: bool = False
) -> str:
    """
    Create an excuse request for late arrival or early departure.

    ⚠️ CRITICAL: DO NOT call this tool until you have:
    1. Gathered ALL required information from the user
    2. Shown a summary to the user
    3. Received EXPLICIT confirmation ("yes", "نعم", "تمام", "أكيد")
    4. Set user_confirmed=True ONLY after receiving explicit confirmation!

    🛑 MANDATORY CONFIRMATION FLOW:
    1. Show summary: "Here's your excuse request: Date: X, Type: Y, Time: Z, Reason: W. Do you want to submit?"
    2. Wait for user to say "yes" / "نعم" / "تمام" / "confirm"
    3. ONLY THEN call this function with user_confirmed=True

    If user says "no", "لا", "cancel" → DO NOT call this function!

    Required information:
    - excuse_date: If user didn't specify, use TODAY's date from context
    - excuse_type: "late_arrival" or "early_departure"
    - reason: MUST be provided by user - ASK if missing!
    - start_time (for late_arrival): MUST be provided - ASK "What time did you arrive?"
      ⚠️ CRITICAL: Use the EXACT time the user provided (e.g., "8:17", "08:17", "8.17").
      DO NOT round, normalize, or modify the time. Pass it exactly as the user said it.
    - end_time (for early_departure): MUST be provided - ASK "What time did you leave?"
      ⚠️ CRITICAL: Use the EXACT time the user provided. DO NOT round or modify it.
    - user_confirmed: MUST be True - only set this after user explicitly confirms!

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        excuse_date: Date of the excuse in YYYY-MM-DD format (use today if not specified)
        excuse_type: Type: "late_arrival" or "early_departure"
        reason: Reason for the excuse (REQUIRED - ask user if not provided!)
        start_time: For late arrival, the EXACT arrival time as provided by user (supports "8:17", "08:17", "8.17" formats) - REQUIRED for late_arrival
        end_time: For early departure, the EXACT departure time as provided by user (supports "15:00", "3:00", "15.00" formats) - REQUIRED for early_departure
        user_confirmed: Set to True ONLY after user explicitly confirms the summary. Default is False.

    Returns:
        Success confirmation with excuse ID.
    """
    # CRITICAL: Block if user hasn't confirmed
    if not user_confirmed:
        return """🛑 STOP! You must get user confirmation first!

Please show this summary to the user and ask for confirmation:

📋 **Excuse Request Summary:**
┌────────────────────────────────┐
│ Date:    [excuse_date]         │
│ Type:    [excuse_type]         │
│ Time:    [time]                │
│ Reason:  [reason]              │
└────────────────────────────────┘

"Do you want to submit this excuse? (Yes/No)"
"هل تريد تقديم هذا الاستئذان؟ (نعم/لا)"

ONLY call create_excuse with user_confirmed=True after user says "yes" or "نعم".
"""
    # VALIDATION: Block if required info is missing
    if not reason or reason.strip() == "":
        return """❌ لا يمكن تسجيل الاستئذان بدون سبب!
        
من فضلك اسأل المستخدم:
"ما سبب التأخير/المغادرة المبكرة؟ (مثال: زحمة، موعد طبي، ظرف عائلي)"

❌ Cannot submit excuse without a reason!
Please ask the user: "What was the reason for being late/leaving early?"
"""

    # VALIDATION: Block generic/hallucinated reasons
    generic_reasons = [
        "late", "late arrival", "delayed", "coming late", "traffic", "unspecified", 
        "reason", "excuse", "تأخر", "تأخير", "زحمة", "بدون سبب", "سبب", "متاخر",
        "نسيت", "forgot", "forgot to submit", "نسيت اقدم", "نسيت اقدم طلب",
        "i forgot", "i was late", "كان متأخر", "تأخرت"
    ]
    
    reason_lower = reason.lower().strip()
    
    # Block if reason is too generic or just describes the action
    if reason_lower in generic_reasons:
        return """❌ السبب المقدم غير كافٍ. يرجى طلب سبب محدد من المستخدم.

من فضلك اسأل المستخدم:
"ما هو السبب المحدد للتأخير/المغادرة المبكرة؟ (مثال: زحمة مرورية على الطريق السريع، موعد طبي، ظرف عائلي طارئ)"

❌ The provided reason is insufficient. Please ask the user for a specific reason.

Please ask: "What was the specific reason for being late/leaving early? (e.g., traffic jam on the highway, medical appointment, family emergency)"
"""
    
    # Block if reason is too short (less than 5 characters) or just one word
    if len(reason.strip()) < 5 or len(reason.split()) < 2:
        return """❌ يرجى طلب سبب أكثر تفصيلاً من المستخدم.

من فضلك اسأل المستخدم:
"ما هو السبب المحدد للتأخير/المغادرة المبكرة؟"

❌ Please ask the user for a more detailed reason.

Please ask: "What was the specific reason for being late/leaving early?"
"""

    # VALIDATION: Check for suspicious times (LLM hallucination of duration as time)
    # Example: User says "30 mins late", LLM sends "00:30". This must be blocked.
    suspicious_time = False
    time_val = start_time if excuse_type == "late_arrival" else end_time
    
    if time_val:
        try:
            h = int(time_val.split(':')[0])
            if 0 <= h < 6:  # Block times between 00:00 and 05:59
                suspicious_time = True
        except:
            pass
            
    if suspicious_time:
        return f"""❌ Error: Time '{time_val}' looks suspicious (too early). 
Did the user say a duration (e.g. "30 mins") and you interpreted it as a time?

You MUST ASK the user for the specific CLOCK TIME.
Example: "You said you were late 30 mins. What time did you actually arrive?"
"""

    if excuse_type == "late_arrival" and not start_time:
        return """❌ لا يمكن تسجيل استئذان التأخر بدون وقت الوصول!

من فضلك اسأل المستخدم:
"كم كانت الساعة عند وصولك؟ (مثال: 8:30)"

❌ Cannot submit late arrival excuse without arrival time!
Please ask: "What time did you arrive?"
"""

    if excuse_type == "early_departure" and not end_time:
        return """❌ لا يمكن تسجيل استئذان المغادرة المبكرة بدون وقت المغادرة!

من فضلك اسأل المستخدم:
"كم كانت الساعة عند مغادرتك؟ (مثال: 15:00)"

❌ Cannot submit early departure excuse without departure time!
Please ask: "What time did you leave?"
"""

    with get_db_session() as db:
        service = HRService(db)
        try:
            exc_date = datetime.strptime(excuse_date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: Invalid date format. Please use YYYY-MM-DD."
            
        result = service.create_excuse(
            employee_id, exc_date, excuse_type, start_time, end_time, reason
        )
        
        # Handle error responses
        if isinstance(result, dict) and result.get("error"):
            return f"❌ Error: {result['error']}"
        
        # Return success message in Arabic if available
        if isinstance(result, dict) and result.get("success"):
            return result.get("message_ar", result.get("message", str(result)))
        
        return str(result)


def create_support_ticket(
    employee_id: str,
    category: str,
    description: str
) -> str:
    """
    Create a new support ticket or complaint.

    ⚠️ IMPORTANT: This tool is for IT, Facilities, Payroll issues ONLY.
    DO NOT use this tool for resignation requests!

    For resignation: Have an empathetic conversation with the employee first,
    then guide them to contact HR directly.

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        category: Category of the ticket - ONLY: "IT", "Facilities", "Payroll"
                  DO NOT use "HR" or "Resignation" categories!
        description: Detailed description of the issue

    Returns:
        Success confirmation with ticket ID.
    """
    # Check if this is a resignation-related ticket - ALWAYS BLOCK
    resignation_keywords = ['استقال', 'resign', 'quit', 'ترك العمل', 'مغادرة', 'انهاء خدم', 'إنهاء خدم', 'termination', 'leaving job', 'resignation']
    desc_lower = description.lower()
    cat_lower = category.lower() if category else ""

    is_resignation = any(keyword in desc_lower for keyword in resignation_keywords) or 'resign' in cat_lower

    print(f"[DEBUG] create_support_ticket: category='{category}', is_resignation={is_resignation}")

    if is_resignation:
        return """❌ لا يمكن إنشاء تذكرة استقالة عبر هذا النظام.

بدلاً من ذلك، يجب عليك كمستشار مهني أن تتحدث مع الموظف أولاً:

1. قل: "أسمعك وأفهم شعورك. هل تسمح لي أن نتحدث عن هذا؟ ما الذي دفعك للتفكير في هذه الخطوة؟"

2. اسأل عن السبب:
   - هل هناك عرض عمل آخر؟ ← ساعده في تحليل العرض (المزايا، التأمين، المسافة)
   - هل المشكلة في الراتب؟ ← اقترح عليه التفاوض مع مديره
   - هل المشكلة في بيئة العمل أو المدير؟ ← اعرض عليه فتح تذكرة سرية للنقاش

3. فقط بعد هذه المحادثة الكاملة، وإذا أصر على الاستقالة، أخبره:
   "أحترم قرارك. للبدء في الإجراءات الرسمية، يرجى التواصل مع قسم الموارد البشرية مباشرة على hr@company.com أو الاتصال بالرقم الداخلي 100."

الآن، ابدأ المحادثة التعاطفية مع الموظف!"""

    with get_db_session() as db:
        service = HRService(db)
        result = service.create_support_ticket(employee_id, category, description)
        return str(result)


# ============================================
# TOOL REGISTRY
# ============================================

def get_hr_tools() -> list:
    """Get all HR tools for the LlamaIndex agent."""
    return [
        # Read tools
        FunctionTool.from_defaults(fn=get_employee_profile),
        FunctionTool.from_defaults(fn=get_leave_balance),
        FunctionTool.from_defaults(fn=get_team_members),
        FunctionTool.from_defaults(fn=get_team_calendar),
        FunctionTool.from_defaults(fn=get_payslip),
        FunctionTool.from_defaults(fn=get_ticket_status),
        FunctionTool.from_defaults(fn=check_duplicate_excuse),
        # Write tools
        FunctionTool.from_defaults(fn=submit_leave_request),
        FunctionTool.from_defaults(fn=create_excuse),
        FunctionTool.from_defaults(fn=create_support_ticket),
    ]
