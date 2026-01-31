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
        EXACT text to display to user - DO NOT REPHRASE OR SUMMARIZE!
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_leave_balance(employee_id, leave_type)

        if isinstance(result, dict) and "balances" in result:
            balances = result["balances"]

            # Build the EXACT response text
            lines = []
            lines.append("**Your Leave Balance:**")
            lines.append("")
            for b in balances:
                leave_name = b["type"].title()
                days = b["remaining_days"]
                if b["type"] == "annual":
                    lines.append(f"- Annual Leave: {days} days remaining")
                elif b["type"] == "sick":
                    lines.append(f"- Sick Leave: {days} days remaining")
                elif b["type"] == "unpaid":
                    lines.append(f"- Unpaid Leave: {days} days remaining")
            lines.append("")
            lines.append("Would you like me to help you request a new leave now?")

            return "\n".join(lines)

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


def get_payslip(employee_id: str, month: Optional[int] = None, year: Optional[int] = None, user_said_latest: bool = False) -> str:
    """
    Get the payslip for an employee.

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        month: Month number (1-12). Leave empty to get latest.
        year: Year (e.g., 2024).
        user_said_latest: Set True if user said "latest" or "الأخير".

    Returns:
        Payslip with full breakdown and download note.
    """
    with get_db_session() as db:
        service = HRService(db)
        result = service.get_payslip(employee_id, month, year)

        if isinstance(result, dict) and not result.get("error"):
            # Build formatted payslip response
            p = result
            period = p.get("period_display", p.get("period", ""))
            basic = p.get("basic_salary", 0)
            net = p.get("net_salary", 0)
            allowances = p.get("allowances", {})
            deductions = p.get("deductions", {})

            lines = [f"**Payslip for {period}:**", ""]
            lines.append(f"Basic Salary: SAR {basic:,.0f}")
            lines.append("")
            lines.append("**Allowances:**")
            lines.append(f"- Housing: SAR {allowances.get('housing_allowance', 0):,.0f}")
            lines.append(f"- Transport: SAR {allowances.get('transport_allowance', 0):,.0f}")
            lines.append(f"- Phone: SAR {allowances.get('phone_allowance', 0):,.0f}")
            lines.append(f"- Meal: SAR {allowances.get('meal_allowance', 0):,.0f}")
            lines.append(f"- Other: SAR {allowances.get('other_allowances', 0):,.0f}")
            lines.append(f"- **Total Allowances: SAR {allowances.get('total', 0):,.0f}**")
            lines.append("")
            lines.append("**Deductions:**")
            lines.append(f"- GOSI: SAR {deductions.get('gosi_deduction', 0):,.0f}")
            lines.append(f"- Tax: SAR {deductions.get('tax_deduction', 0):,.0f}")
            lines.append(f"- Loan: SAR {deductions.get('loan_deduction', 0):,.0f}")
            lines.append(f"- **Total Deductions: SAR {deductions.get('total', 0):,.0f}**")
            lines.append("")
            lines.append(f"**Net Salary: SAR {net:,.0f}**")
            lines.append("")
            lines.append("Download option coming soon!")

            return "\n".join(lines)

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
# UTILITY TOOLS
# ============================================

def handle_cancel_request(user_message: str) -> str:
    """
    Check if the user wants to cancel the current operation.

    Call this tool when the user says: cancel, stop, abort, never mind, إلغاء, توقف, لا أريد, خلاص

    Args:
        user_message: The user's message to check for cancel intent.

    Returns:
        Confirmation that the operation was cancelled.
    """
    cancel_keywords = ["cancel", "stop", "abort", "never mind", "nevermind", "forget it",
                       "إلغاء", "توقف", "لا أريد", "خلاص", "الغاء", "لا", "كنسل"]

    msg_lower = user_message.lower().strip()

    if any(keyword in msg_lower for keyword in cancel_keywords):
        return """{"cancelled": true, "message": "No problem! The request has been cancelled. How else can I help you?", "message_ar": "لا مشكلة! تم إلغاء الطلب. كيف يمكنني مساعدتك؟"}"""

    return """{"cancelled": false, "message": "This doesn't appear to be a cancel request."}"""


# ============================================
# WRITE TOOLS
# ============================================

def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: Optional[str] = None,
    confirm_conflicts: bool = False
) -> str:
    """
    Submit a new leave request for an employee.

    ⚠️ CONFLICT HANDLING:
    - First call with confirm_conflicts=False (default) - checks for team conflicts
    - If result contains "warning": "team_conflict":
      * Tell the user about conflicting team members
      * Ask if they want to proceed anyway
    - If user confirms, call again with confirm_conflicts=True

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        leave_type: Type of leave: "annual", "sick", or "unpaid"
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        reason: Optional reason for the leave
        confirm_conflicts: Set to True ONLY after user confirms despite team conflicts

    Returns:
        - If conflicts exist and confirm_conflicts=False: Warning with conflict details
        - If no conflicts or confirm_conflicts=True: Success with request ID
        - Error if validation fails
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

        # Submit the request - the service handles conflict checking
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
    end_time: Optional[str] = None
) -> str:
    """
    Create an excuse request for late arrival or early departure.

    ⚠️ CRITICAL: DO NOT call this tool until you have gathered ALL required information:
    - excuse_date: If user didn't specify, use TODAY's date from context
    - excuse_type: "late_arrival" or "early_departure"
    - reason: MUST be provided by user - ASK if missing!
    - start_time (for late_arrival): MUST be provided - ASK "What time did you arrive?"
      ⚠️ CRITICAL: Use the EXACT time the user provided (e.g., "8:17", "08:17", "8.17").
      DO NOT round, normalize, or modify the time. Pass it exactly as the user said it.
    - end_time (for early_departure): MUST be provided - ASK "What time did you leave?"
      ⚠️ CRITICAL: Use the EXACT time the user provided. DO NOT round or modify it.

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        excuse_date: Date of the excuse in YYYY-MM-DD format (use today if not specified)
        excuse_type: Type: "late_arrival" or "early_departure"
        reason: Reason for the excuse (REQUIRED - ask user if not provided!)
        start_time: For late arrival, the EXACT arrival time as provided by user (supports "8:17", "08:17", "8.17" formats) - REQUIRED for late_arrival
        end_time: For early departure, the EXACT departure time as provided by user (supports "15:00", "3:00", "15.00" formats) - REQUIRED for early_departure

    Returns:
        Success confirmation with excuse ID.
    """
    # ============================================
    # VALIDATION 1: TIME IS MANDATORY - CHECK FIRST!
    # ============================================
    if excuse_type == "late_arrival" and not start_time:
        return """{"error": "missing_arrival_time", "message_ar": "لا يمكن تسجيل استئذان التأخر بدون وقت الوصول! اسأل المستخدم: كم كانت الساعة عند وصولك؟", "message": "Cannot submit late arrival excuse without arrival time! Ask the user: What time did you arrive? (e.g., 8:30)"}"""

    if excuse_type == "early_departure" and not end_time:
        return """{"error": "missing_departure_time", "message_ar": "لا يمكن تسجيل استئذان المغادرة المبكرة بدون وقت المغادرة! اسأل المستخدم: كم كانت الساعة عند مغادرتك؟", "message": "Cannot submit early departure excuse without departure time! Ask the user: What time did you leave? (e.g., 15:00)"}"""

    # ============================================
    # VALIDATION 2: REASON IS MANDATORY
    # ============================================
    if not reason or reason.strip() == "":
        return """{"error": "missing_reason", "message_ar": "لا يمكن تسجيل الاستئذان بدون سبب! اسأل المستخدم: ما سبب التأخير/المغادرة المبكرة؟", "message": "Cannot submit excuse without a reason! Ask the user: What was the reason for being late/leaving early?"}"""

    # ============================================
    # VALIDATION 3: BLOCK GENERIC/HALLUCINATED REASONS
    # ============================================
    generic_reasons = [
        "late", "late arrival", "delayed", "coming late", "traffic", "unspecified",
        "reason", "excuse", "personal", "personal reason", "personal reasons",
        "sick", "not feeling well", "unwell",
        # Arabic generic reasons
        "تأخر", "تأخير", "زحمة", "بدون سبب", "سبب", "متاخر", "شخصي", "ظروف",
        "نسيت", "forgot", "forgot to submit", "نسيت اقدم", "نسيت اقدم طلب",
        "i forgot", "i was late", "كان متأخر", "تأخرت", "مريض", "تعبان"
    ]

    reason_lower = reason.lower().strip()

    if reason_lower in generic_reasons:
        return """{"error": "generic_reason", "message_ar": "السبب المقدم غير كافٍ. اسأل المستخدم: ما هو السبب المحدد؟ (مثال: زحمة مرورية على الطريق السريع، موعد طبي، ظرف عائلي طارئ)", "message": "The provided reason is too generic. Ask the user: What was the specific reason? (e.g., traffic jam on highway, medical appointment, family emergency)"}"""

    # Block if reason is too short (less than 8 characters) or just one/two words
    if len(reason.strip()) < 8 or len(reason.split()) < 2:
        return """{"error": "reason_too_short", "message_ar": "يرجى طلب سبب أكثر تفصيلاً من المستخدم.", "message": "Please ask the user for a more detailed reason."}"""

    # ============================================
    # VALIDATION 4: CHECK FOR SUSPICIOUS TIMES
    # ============================================
    time_val = start_time if excuse_type == "late_arrival" else end_time

    if time_val:
        try:
            h = int(time_val.split(':')[0].replace('.', ':').split(':')[0])
            # Block times between 00:00 and 05:59 (suspicious - probably hallucinated)
            if 0 <= h < 6:
                return f"""{{"error": "suspicious_time", "message": "Time '{time_val}' looks suspicious (too early). Did the user say a duration? Ask for the actual clock time.", "message_ar": "الوقت '{time_val}' يبدو غير صحيح. اسأل المستخدم عن الوقت الفعلي."}}"""
        except:
            pass

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
        # Utility tools
        FunctionTool.from_defaults(fn=handle_cancel_request),
        # Write tools
        FunctionTool.from_defaults(fn=submit_leave_request),
        FunctionTool.from_defaults(fn=create_excuse),
        FunctionTool.from_defaults(fn=create_support_ticket),
    ]
