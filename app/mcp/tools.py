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
    confirm_conflicts: bool = False
) -> str:
    """
    Submit a new leave request for an employee.

    ⚠️ CRITICAL: DO NOT call this tool until you have ALL required information from the user:
    - leave_type: The user MUST specify annual, sick, or unpaid
    - start_date: The user MUST provide the start date
    - end_date: The user MUST provide the end date

    If ANY of these are missing, ASK THE USER first. Do NOT invent or assume dates.

    ⚠️ WORKFLOW after gathering info:
    1. First call with confirm_conflicts=False (default)
    2. If result contains "warning": "team_conflict", you MUST:
       - Tell the user about the conflicting team members
       - Ask if they want to proceed anyway
    3. Only if user confirms, call again with confirm_conflicts=True

    Args:
        employee_id: The employee ID (e.g., "EMP001")
        leave_type: Type of leave: "annual", "sick", or "unpaid"
        start_date: Start date in YYYY-MM-DD format (MUST be provided by user, not invented!)
        end_date: End date in YYYY-MM-DD format (MUST be provided by user, not invented!)
        reason: Optional reason for the leave
        confirm_conflicts: Set to True ONLY after user confirms they want to proceed despite team conflicts

    Returns:
        - If conflicts exist and confirm_conflicts=False: Warning with conflict details
        - If no conflicts or confirm_conflicts=True: Success confirmation with request ID
        - Error if validation fails (insufficient balance, invalid dates, etc.)
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
    
    Args:
        employee_id: The employee ID (e.g., "EMP001")
        excuse_date: Date of the excuse in YYYY-MM-DD format
        excuse_type: Type: "late_arrival" or "early_departure"
        reason: Reason for the excuse (required)
        start_time: For late arrival, the actual arrival time (HH:MM format)
        end_time: For early departure, the departure time (HH:MM format)
    
    Returns:
        Success confirmation with excuse ID.
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
        return str(result)


def create_support_ticket(
    employee_id: str,
    category: str,
    description: str
) -> str:
    """
    Create a new support ticket or complaint.
    
    Args:
        employee_id: The employee ID (e.g., "EMP001")
        category: Category of the ticket (e.g., "IT", "HR", "Facilities", "Payroll")
        description: Detailed description of the issue
    
    Returns:
        Success confirmation with ticket ID.
    """
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
        # Write tools
        FunctionTool.from_defaults(fn=submit_leave_request),
        FunctionTool.from_defaults(fn=create_excuse),
        FunctionTool.from_defaults(fn=create_support_ticket),
    ]
