"""Pydantic Schemas for Strict Output Validation.

These schemas enforce structured outputs to prevent LLM hallucinations
and ensure consistent response formats across all HR operations.
"""

from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================
# LANGUAGE AND INTENT SCHEMAS
# ============================================

class IntentClassification(BaseModel):
    """Schema for intent detection results."""
    intent: Literal[
        "leave_balance",
        "leave_request",
        "payslip",
        "excuse",
        "policy",
        "cancel",
        "greeting",
        "general"
    ] = Field(description="The detected user intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    language: Literal["en", "ar"] = Field(description="Detected language: en=English, ar=Arabic")
    reasoning: Optional[str] = Field(default=None, description="Chain of thought reasoning")


# ============================================
# LEAVE BALANCE SCHEMAS
# ============================================

class LeaveBalanceItem(BaseModel):
    """Single leave type balance."""
    leave_type: Literal["annual", "sick", "unpaid"] = Field(description="Type of leave")
    leave_type_display: str = Field(description="Display name (e.g., 'Annual Leave')")
    leave_type_ar: str = Field(description="Arabic display name")
    remaining_days: int = Field(ge=0, description="Days remaining")
    emoji: str = Field(default="", description="Emoji for display")


class LeaveBalanceResponse(BaseModel):
    """Structured response for leave balance queries."""
    success: bool = Field(default=True)
    employee_id: str = Field(description="Employee ID")
    balances: List[LeaveBalanceItem] = Field(description="List of leave balances")
    language: Literal["en", "ar"] = Field(description="Response language")
    follow_up_question: str = Field(
        description="Mandatory follow-up question to ask user"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")
    reasoning: Optional[str] = Field(default=None, description="Chain of thought")

    @field_validator('follow_up_question', mode='before')
    @classmethod
    def ensure_follow_up(cls, v, info):
        """Ensure follow-up question is present."""
        if not v:
            lang = info.data.get('language', 'en')
            if lang == 'ar':
                return "هل تريد مساعدتك في طلب إجازة جديدة الآن؟"
            return "Would you like me to help you request a new leave now?"
        return v


# ============================================
# LEAVE REQUEST SCHEMAS
# ============================================

class BalanceImpact(BaseModel):
    """Shows balance before and after a request."""
    original: int = Field(ge=0, description="Original balance")
    used: int = Field(ge=0, description="Days being used")
    remaining: int = Field(ge=0, description="Balance after approval")


class LeaveRequestPreview(BaseModel):
    """Preview schema before leave submission - requires user confirmation."""
    preview: bool = Field(default=True, description="Indicates this is a preview")
    not_submitted_yet: bool = Field(default=True, description="Request not yet submitted")
    employee_id: str = Field(description="Employee ID")
    leave_type: Literal["annual", "sick", "unpaid"] = Field(description="Type of leave")
    leave_type_display: str = Field(description="Display name for leave type")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    days: int = Field(gt=0, description="Number of days requested")
    balance_impact: BalanceImpact = Field(description="Balance before/after")
    has_conflict: bool = Field(default=False, description="Team conflict detected")
    conflict_details: Optional[List[str]] = Field(default=None, description="Conflict details")
    language: Literal["en", "ar"] = Field(description="Response language")
    confirmation_prompt: str = Field(
        description="Question asking user to confirm submission"
    )
    error: Optional[str] = Field(default=None, description="Validation error if any")
    reasoning: Optional[str] = Field(default=None, description="Chain of thought")

    @field_validator('confirmation_prompt', mode='before')
    @classmethod
    def ensure_confirmation(cls, v, info):
        """Ensure confirmation prompt is present."""
        if not v:
            lang = info.data.get('language', 'en')
            if lang == 'ar':
                return "هل تريد تقديم هذا الطلب؟ (نعم/لا)"
            return "Do you want to submit this request? (Yes/No)"
        return v


class LeaveRequestResult(BaseModel):
    """Result after successful leave submission."""
    success: bool = Field(default=True)
    request_id: str = Field(description="Generated request ID (e.g., LR-0001)")
    employee_id: str = Field(description="Employee ID")
    leave_type: str = Field(description="Type of leave")
    start_date: str = Field(description="Start date")
    end_date: str = Field(description="End date")
    days: int = Field(description="Number of days")
    status: str = Field(default="pending", description="Request status")
    balance_info: BalanceImpact = Field(description="Balance impact details")
    message: str = Field(description="Success message in appropriate language")
    language: Literal["en", "ar"] = Field(description="Response language")
    error: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)


# ============================================
# EXCUSE REQUEST SCHEMAS
# ============================================

class ExcuseRequestPreview(BaseModel):
    """Preview schema before excuse submission - requires user confirmation."""
    preview: bool = Field(default=True)
    not_submitted_yet: bool = Field(default=True)
    employee_id: str = Field(description="Employee ID")
    excuse_date: str = Field(description="Date of excuse YYYY-MM-DD")
    excuse_type: Literal["late_arrival", "early_departure"] = Field(
        description="Type of excuse"
    )
    excuse_type_display: str = Field(description="Display name for excuse type")
    time: str = Field(description="Arrival or departure time")
    reason: str = Field(min_length=10, description="Detailed reason for excuse")
    language: Literal["en", "ar"] = Field(description="Response language")
    confirmation_prompt: str = Field(
        description="Question asking user to confirm submission"
    )
    error: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)

    @field_validator('confirmation_prompt', mode='before')
    @classmethod
    def ensure_confirmation(cls, v, info):
        """Ensure confirmation prompt is present."""
        if not v:
            lang = info.data.get('language', 'en')
            if lang == 'ar':
                return "هل تريد تقديم هذا الاستئذان؟ (نعم/لا)"
            return "Do you want to submit this excuse? (Yes/No)"
        return v


class ExcuseRequestResult(BaseModel):
    """Result after successful excuse submission."""
    success: bool = Field(default=True)
    excuse_id: str = Field(description="Generated excuse ID (e.g., EX-0001)")
    employee_id: str = Field(description="Employee ID")
    excuse_date: str = Field(description="Date of excuse")
    excuse_type: str = Field(description="Type of excuse")
    time: str = Field(description="Time recorded")
    reason: str = Field(description="Reason provided")
    status: str = Field(default="pending", description="Excuse status")
    message: str = Field(description="Success message in appropriate language")
    language: Literal["en", "ar"] = Field(description="Response language")
    error: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)


# ============================================
# PAYSLIP SCHEMAS
# ============================================

class PayslipAllowances(BaseModel):
    """Breakdown of payslip allowances."""
    housing: float = Field(ge=0, description="Housing allowance")
    transport: float = Field(ge=0, description="Transport allowance")
    phone: float = Field(ge=0, description="Phone allowance")
    meal: float = Field(ge=0, description="Meal allowance")
    other: float = Field(ge=0, description="Other allowances")
    total: float = Field(ge=0, description="Total allowances")


class PayslipDeductions(BaseModel):
    """Breakdown of payslip deductions."""
    gosi: float = Field(ge=0, description="GOSI/Social insurance")
    tax: float = Field(ge=0, description="Tax deduction")
    loan: float = Field(ge=0, description="Loan repayment")
    absence: float = Field(ge=0, default=0, description="Absence deduction")
    other: float = Field(ge=0, description="Other deductions")
    total: float = Field(ge=0, description="Total deductions")


class PayslipResponse(BaseModel):
    """Structured response for payslip queries."""
    success: bool = Field(default=True)
    employee_id: str = Field(description="Employee ID")
    period: str = Field(description="Period (e.g., 'January 2026')")
    period_ar: str = Field(description="Arabic period display")
    basic_salary: float = Field(ge=0, description="Basic salary")
    allowances: PayslipAllowances = Field(description="Allowances breakdown")
    deductions: PayslipDeductions = Field(description="Deductions breakdown")
    net_salary: float = Field(ge=0, description="Net salary after deductions")
    download_url: str = Field(description="URL to download PDF payslip")
    language: Literal["en", "ar"] = Field(description="Response language")
    error: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)


# ============================================
# ERROR RESPONSE SCHEMA
# ============================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = Field(default=False)
    error_code: str = Field(description="Error code for programmatic handling")
    message: str = Field(description="User-friendly error message in English")
    message_ar: str = Field(description="User-friendly error message in Arabic")
    suggestion: Optional[str] = Field(default=None, description="Suggested action")
    language: Literal["en", "ar"] = Field(description="Detected language")


# ============================================
# MISSING INFO SCHEMA
# ============================================

class MissingInfoRequest(BaseModel):
    """Schema for requesting missing information from user."""
    intent: str = Field(description="Current intent being processed")
    missing_fields: List[str] = Field(description="List of missing required fields")
    question: str = Field(description="Question to ask user in their language")
    language: Literal["en", "ar"] = Field(description="Response language")
    current_data: dict = Field(default_factory=dict, description="Data collected so far")


# ============================================
# DUPLICATE DETECTION SCHEMA
# ============================================

class DuplicateDetectionResult(BaseModel):
    """Result of duplicate message detection."""
    is_duplicate: bool = Field(description="Whether this is a duplicate request")
    original_message_index: Optional[int] = Field(
        default=None,
        description="Index of original message in history if duplicate"
    )
    message_fingerprint: str = Field(description="Hash of normalized message")
    suggested_response: Optional[str] = Field(
        default=None,
        description="Suggested response if duplicate detected"
    )
