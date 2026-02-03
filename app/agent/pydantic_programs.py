"""Pydantic Programs for Structured LLM Outputs.

This module provides structured output enforcement using Pydantic schemas
to eliminate hallucinations and ensure consistent response formats.
"""

import hashlib
import json
from typing import Optional, Type, TypeVar, List, Dict, Any
from pydantic import BaseModel, ValidationError

from app.agent.schemas import (
    IntentClassification,
    LeaveBalanceResponse, LeaveBalanceItem,
    LeaveRequestPreview, LeaveRequestResult, BalanceImpact,
    ExcuseRequestPreview, ExcuseRequestResult,
    PayslipResponse, PayslipAllowances, PayslipDeductions,
    ErrorResponse, MissingInfoRequest, DuplicateDetectionResult
)

T = TypeVar('T', bound=BaseModel)


# ============================================
# INTENT TO SCHEMA MAPPING
# ============================================

INTENT_SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "leave_balance": LeaveBalanceResponse,
    "leave_request_preview": LeaveRequestPreview,
    "leave_request_result": LeaveRequestResult,
    "excuse_preview": ExcuseRequestPreview,
    "excuse_result": ExcuseRequestResult,
    "payslip": PayslipResponse,
    "intent_classification": IntentClassification,
    "error": ErrorResponse,
    "missing_info": MissingInfoRequest,
}


# ============================================
# STRUCTURED OUTPUT BUILDER
# ============================================

class StructuredOutputBuilder:
    """
    Builds structured outputs matching Pydantic schemas.
    Ensures all required fields are present and valid.
    """

    @staticmethod
    def build_leave_balance_response(
        employee_id: str,
        balances: List[Dict],
        language: str = "en"
    ) -> LeaveBalanceResponse:
        """Build a structured leave balance response."""
        balance_items = []

        for b in balances:
            leave_type = b.get("type", "").lower()
            remaining = b.get("remaining_days", 0)

            # Map leave types to display names and emojis
            type_info = {
                "annual": {
                    "display": "Annual Leave",
                    "ar": "إجازة سنوية",
                    "emoji": "🏖️"
                },
                "sick": {
                    "display": "Sick Leave",
                    "ar": "إجازة مرضية",
                    "emoji": "🏥"
                },
                "unpaid": {
                    "display": "Unpaid Leave",
                    "ar": "إجازة بدون راتب",
                    "emoji": "📝"
                }
            }

            info = type_info.get(leave_type, {
                "display": leave_type.title(),
                "ar": leave_type,
                "emoji": "📋"
            })

            balance_items.append(LeaveBalanceItem(
                leave_type=leave_type,
                leave_type_display=info["display"],
                leave_type_ar=info["ar"],
                remaining_days=remaining,
                emoji=info["emoji"]
            ))

        follow_up = (
            "هل تريد مساعدتك في طلب إجازة جديدة الآن؟"
            if language == "ar"
            else "Would you like me to help you request a new leave now?"
        )

        return LeaveBalanceResponse(
            success=True,
            employee_id=employee_id,
            balances=balance_items,
            language=language,
            follow_up_question=follow_up
        )

    @staticmethod
    def build_leave_request_preview(
        employee_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        days: int,
        current_balance: int,
        language: str = "en",
        has_conflict: bool = False,
        conflict_details: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> LeaveRequestPreview:
        """Build a leave request preview response."""
        # Map leave types
        type_display = {
            "annual": "Annual Leave" if language == "en" else "إجازة سنوية",
            "sick": "Sick Leave" if language == "en" else "إجازة مرضية",
            "unpaid": "Unpaid Leave" if language == "en" else "إجازة بدون راتب"
        }

        remaining = current_balance - days if leave_type != "unpaid" else current_balance

        confirmation = (
            "هل تريد تقديم هذا الطلب؟ (نعم/لا)"
            if language == "ar"
            else "Do you want to submit this request? (Yes/No)"
        )

        return LeaveRequestPreview(
            preview=True,
            not_submitted_yet=True,
            employee_id=employee_id,
            leave_type=leave_type,
            leave_type_display=type_display.get(leave_type, leave_type.title()),
            start_date=start_date,
            end_date=end_date,
            days=days,
            balance_impact=BalanceImpact(
                original=current_balance,
                used=days,
                remaining=max(0, remaining)
            ),
            has_conflict=has_conflict,
            conflict_details=conflict_details,
            language=language,
            confirmation_prompt=confirmation,
            error=error
        )

    @staticmethod
    def build_leave_request_result(
        request_id: str,
        employee_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        days: int,
        original_balance: int,
        remaining_balance: int,
        language: str = "en"
    ) -> LeaveRequestResult:
        """Build a leave request result after submission."""
        if language == "ar":
            message = f"تم تقديم طلب الإجازة بنجاح! رقم الطلب: {request_id}. رصيد إجازتك الآن {remaining_balance} يوم."
        else:
            message = f"Leave request submitted successfully! Request ID: {request_id}. Your leave balance is now {remaining_balance} days."

        return LeaveRequestResult(
            success=True,
            request_id=request_id,
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days=days,
            status="pending",
            balance_info=BalanceImpact(
                original=original_balance,
                used=days,
                remaining=remaining_balance
            ),
            message=message,
            language=language
        )

    @staticmethod
    def build_excuse_preview(
        employee_id: str,
        excuse_date: str,
        excuse_type: str,
        time: str,
        reason: str,
        language: str = "en"
    ) -> ExcuseRequestPreview:
        """Build an excuse request preview response."""
        type_display = {
            "late_arrival": "Late Arrival" if language == "en" else "تأخر في الحضور",
            "early_departure": "Early Departure" if language == "en" else "مغادرة مبكرة"
        }

        confirmation = (
            "هل تريد تقديم هذا الاستئذان؟ (نعم/لا)"
            if language == "ar"
            else "Do you want to submit this excuse? (Yes/No)"
        )

        return ExcuseRequestPreview(
            preview=True,
            not_submitted_yet=True,
            employee_id=employee_id,
            excuse_date=excuse_date,
            excuse_type=excuse_type,
            excuse_type_display=type_display.get(excuse_type, excuse_type),
            time=time,
            reason=reason,
            language=language,
            confirmation_prompt=confirmation
        )

    @staticmethod
    def build_excuse_result(
        excuse_id: str,
        employee_id: str,
        excuse_date: str,
        excuse_type: str,
        time: str,
        reason: str,
        language: str = "en"
    ) -> ExcuseRequestResult:
        """Build an excuse request result after submission."""
        if language == "ar":
            message = f"تم تسجيل طلب الاستئذان بنجاح! رقم الطلب: {excuse_id}."
        else:
            message = f"Excuse request submitted successfully! Request ID: {excuse_id}."

        return ExcuseRequestResult(
            success=True,
            excuse_id=excuse_id,
            employee_id=employee_id,
            excuse_date=excuse_date,
            excuse_type=excuse_type,
            time=time,
            reason=reason,
            status="pending",
            message=message,
            language=language
        )

    @staticmethod
    def build_payslip_response(
        employee_id: str,
        period: str,
        period_ar: str,
        basic_salary: float,
        allowances: Dict[str, float],
        deductions: Dict[str, float],
        net_salary: float,
        download_url: str,
        language: str = "en"
    ) -> PayslipResponse:
        """Build a structured payslip response."""
        return PayslipResponse(
            success=True,
            employee_id=employee_id,
            period=period,
            period_ar=period_ar,
            basic_salary=basic_salary,
            allowances=PayslipAllowances(
                housing=allowances.get("housing_allowance", 0),
                transport=allowances.get("transport_allowance", 0),
                phone=allowances.get("phone_allowance", 0),
                meal=allowances.get("meal_allowance", 0),
                other=allowances.get("other_allowances", 0),
                total=allowances.get("total", 0)
            ),
            deductions=PayslipDeductions(
                gosi=deductions.get("gosi_deduction", 0),
                tax=deductions.get("tax_deduction", 0),
                loan=deductions.get("loan_deduction", 0),
                absence=deductions.get("absence_deduction", 0),
                other=deductions.get("other_deductions", 0),
                total=deductions.get("total", 0)
            ),
            net_salary=net_salary,
            download_url=download_url,
            language=language
        )

    @staticmethod
    def build_error_response(
        error_code: str,
        message: str,
        message_ar: str,
        language: str = "en",
        suggestion: Optional[str] = None
    ) -> ErrorResponse:
        """Build a structured error response."""
        return ErrorResponse(
            success=False,
            error_code=error_code,
            message=message,
            message_ar=message_ar,
            suggestion=suggestion,
            language=language
        )

    @staticmethod
    def build_missing_info_request(
        intent: str,
        missing_fields: List[str],
        language: str = "en",
        current_data: Optional[Dict] = None
    ) -> MissingInfoRequest:
        """Build a request for missing information."""
        # Generate appropriate question based on missing fields
        questions = {
            "leave_type": {
                "en": "What type of leave would you like? (Annual, Sick, or Unpaid)",
                "ar": "ما نوع الإجازة التي تريدها؟ (سنوية، مرضية، أو بدون راتب)"
            },
            "start_date": {
                "en": "What is the start date for your leave? (e.g., 2026-02-01)",
                "ar": "ما هو تاريخ بداية إجازتك؟ (مثال: 2026-02-01)"
            },
            "end_date": {
                "en": "What is the end date for your leave?",
                "ar": "ما هو تاريخ نهاية إجازتك؟"
            },
            "reason": {
                "en": "What is the specific reason? (Please provide details)",
                "ar": "ما هو السبب المحدد؟ (يرجى تقديم التفاصيل)"
            },
            "time": {
                "en": "What time did you arrive/leave? (e.g., 8:30 AM)",
                "ar": "كم كانت الساعة عند وصولك/مغادرتك؟ (مثال: 8:30 صباحاً)"
            },
            "start_time": {
                "en": "What time did you arrive? (e.g., 8:30 AM)",
                "ar": "كم كانت الساعة عند وصولك؟ (مثال: 8:30 صباحاً)"
            },
            "end_time": {
                "en": "What time did you leave? (e.g., 3:00 PM)",
                "ar": "كم كانت الساعة عند مغادرتك؟ (مثال: 3:00 مساءً)"
            },
            "month": {
                "en": "Which month would you like to view? (e.g., January 2026, or 'latest')",
                "ar": "أي شهر تريد عرضه؟ (مثال: يناير 2026، أو 'الأخير')"
            }
        }

        # Combine questions for all missing fields
        question_parts = []
        for field in missing_fields:
            if field in questions:
                q = questions[field][language]
                question_parts.append(q)

        combined_question = " ".join(question_parts) if question_parts else (
            "Please provide more information." if language == "en"
            else "يرجى تقديم المزيد من المعلومات."
        )

        return MissingInfoRequest(
            intent=intent,
            missing_fields=missing_fields,
            question=combined_question,
            language=language,
            current_data=current_data or {}
        )


# ============================================
# DUPLICATE DETECTION
# ============================================

class DuplicateDetector:
    """
    Detects duplicate messages using fingerprinting.
    Prevents processing the same request twice.
    """

    @staticmethod
    def normalize_message(message: str) -> str:
        """Normalize message for fingerprinting."""
        # Remove extra whitespace, lowercase
        normalized = " ".join(message.lower().split())
        # Remove common filler words
        fillers = ["please", "can you", "could you", "i want to", "i need to",
                   "من فضلك", "ممكن", "أريد", "بدي"]
        for filler in fillers:
            normalized = normalized.replace(filler, "")
        return normalized.strip()

    @staticmethod
    def create_fingerprint(message: str, intent: Optional[str] = None) -> str:
        """Create a fingerprint hash for the message."""
        normalized = DuplicateDetector.normalize_message(message)
        if intent:
            normalized = f"{intent}:{normalized}"
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    @staticmethod
    def check_duplicate(
        message: str,
        intent: str,
        chat_history: List[Dict],
        lookback: int = 5
    ) -> DuplicateDetectionResult:
        """
        Check if message is a duplicate of recent messages.

        Args:
            message: Current user message
            intent: Detected intent
            chat_history: Previous messages
            lookback: Number of messages to check

        Returns:
            DuplicateDetectionResult with detection info
        """
        current_fp = DuplicateDetector.create_fingerprint(message, intent)

        # Check recent user messages
        user_messages = [
            (i, msg) for i, msg in enumerate(chat_history[-lookback * 2:])
            if msg.get("role") == "user"
        ]

        for idx, msg in user_messages:
            msg_fp = DuplicateDetector.create_fingerprint(
                msg.get("content", ""), intent
            )
            if msg_fp == current_fp:
                # Found duplicate
                suggested = (
                    "I see you mentioned this earlier. Would you like to continue "
                    "with the previous request or start a new one?"
                )
                return DuplicateDetectionResult(
                    is_duplicate=True,
                    original_message_index=idx,
                    message_fingerprint=current_fp,
                    suggested_response=suggested
                )

        return DuplicateDetectionResult(
            is_duplicate=False,
            message_fingerprint=current_fp
        )


# ============================================
# RESPONSE FORMATTER
# ============================================

class ResponseFormatter:
    """
    Formats structured responses into user-friendly text.
    Maintains consistency with the card-based display format.
    """

    @staticmethod
    def format_leave_balance(response: LeaveBalanceResponse) -> str:
        """Format leave balance response as a card."""
        if response.language == "ar":
            lines = ["📊 **رصيد إجازاتك:**", ""]
            for b in response.balances:
                lines.append(f"{b.emoji} {b.leave_type_ar}: {b.remaining_days} أيام متبقية")
            lines.append("")
            lines.append(response.follow_up_question)
        else:
            lines = ["📊 **Your Leave Balance:**", ""]
            for b in response.balances:
                lines.append(f"{b.emoji} {b.leave_type_display}: {b.remaining_days} days remaining")
            lines.append("")
            lines.append(response.follow_up_question)

        return "\n".join(lines)

    @staticmethod
    def format_leave_preview(response: LeaveRequestPreview) -> str:
        """Format leave request preview as a card."""
        bi = response.balance_impact

        if response.language == "ar":
            lines = [
                "📋 **ملخص طلب الإجازة:**",
                "",
                f"النوع: {response.leave_type_display}",
                f"من: {response.start_date}",
                f"إلى: {response.end_date}",
                f"المدة: {response.days} أيام",
                f"الرصيد: {bi.original} → {bi.remaining} أيام",
                ""
            ]
            if response.has_conflict and response.conflict_details:
                lines.append("⚠️ **تعارض مع الفريق:**")
                for c in response.conflict_details:
                    lines.append(f"  - {c}")
                lines.append("")
            if response.error:
                lines.append(f"❌ {response.error}")
                lines.append("")
            lines.append(response.confirmation_prompt)
        else:
            lines = [
                "📋 **Leave Request Summary:**",
                "",
                f"Type: {response.leave_type_display}",
                f"From: {response.start_date}",
                f"To: {response.end_date}",
                f"Duration: {response.days} days",
                f"Balance: {bi.original} → {bi.remaining} days",
                ""
            ]
            if response.has_conflict and response.conflict_details:
                lines.append("⚠️ **Team Conflict:**")
                for c in response.conflict_details:
                    lines.append(f"  - {c}")
                lines.append("")
            if response.error:
                lines.append(f"❌ {response.error}")
                lines.append("")
            lines.append(response.confirmation_prompt)

        return "\n".join(lines)

    @staticmethod
    def format_leave_result(response: LeaveRequestResult) -> str:
        """Format leave request result."""
        return response.message

    @staticmethod
    def format_excuse_preview(response: ExcuseRequestPreview) -> str:
        """Format excuse request preview as a card."""
        if response.language == "ar":
            lines = [
                "📋 **ملخص طلب الاستئذان:**",
                "",
                f"التاريخ: {response.excuse_date}",
                f"النوع: {response.excuse_type_display}",
                f"الوقت: {response.time}",
                f"السبب: {response.reason}",
                "",
                response.confirmation_prompt
            ]
        else:
            lines = [
                "📋 **Excuse Request Summary:**",
                "",
                f"Date: {response.excuse_date}",
                f"Type: {response.excuse_type_display}",
                f"Time: {response.time}",
                f"Reason: {response.reason}",
                "",
                response.confirmation_prompt
            ]

        return "\n".join(lines)

    @staticmethod
    def format_excuse_result(response: ExcuseRequestResult) -> str:
        """Format excuse request result."""
        return response.message

    @staticmethod
    def format_payslip(response: PayslipResponse) -> str:
        """Format payslip response as a card."""
        a = response.allowances
        d = response.deductions

        if response.language == "ar":
            lines = [
                f"💰 **قسيمة الراتب لشهر {response.period_ar}:**",
                "",
                f"الراتب الأساسي: {response.basic_salary:,.0f} ريال",
                "",
                "**البدلات:**",
                f"  - بدل السكن: {a.housing:,.0f} ريال",
                f"  - بدل المواصلات: {a.transport:,.0f} ريال",
                f"  - بدل الهاتف: {a.phone:,.0f} ريال",
                f"  - بدل الطعام: {a.meal:,.0f} ريال",
                f"  - بدلات أخرى: {a.other:,.0f} ريال",
                f"  - **إجمالي البدلات: {a.total:,.0f} ريال**",
                "",
                "**الاستقطاعات:**",
                f"  - التأمينات (GOSI): {d.gosi:,.0f} ريال",
                f"  - الضريبة: {d.tax:,.0f} ريال",
                f"  - قسط القرض: {d.loan:,.0f} ريال",
                f"  - **إجمالي الاستقطاعات: {d.total:,.0f} ريال**",
                "",
                f"**💵 صافي الراتب: {response.net_salary:,.0f} ريال**",
                "",
                f"[تحميل PDF]({response.download_url})"
            ]
        else:
            lines = [
                f"💰 **Payslip for {response.period}:**",
                "",
                f"Basic Salary: SAR {response.basic_salary:,.0f}",
                "",
                "**Allowances:**",
                f"  - Housing: SAR {a.housing:,.0f}",
                f"  - Transport: SAR {a.transport:,.0f}",
                f"  - Phone: SAR {a.phone:,.0f}",
                f"  - Meal: SAR {a.meal:,.0f}",
                f"  - Other: SAR {a.other:,.0f}",
                f"  - **Total Allowances: SAR {a.total:,.0f}**",
                "",
                "**Deductions:**",
                f"  - GOSI: SAR {d.gosi:,.0f}",
                f"  - Tax: SAR {d.tax:,.0f}",
                f"  - Loan: SAR {d.loan:,.0f}",
                f"  - **Total Deductions: SAR {d.total:,.0f}**",
                "",
                f"**💵 Net Salary: SAR {response.net_salary:,.0f}**",
                "",
                f"[Download PDF]({response.download_url})"
            ]

        return "\n".join(lines)

    @staticmethod
    def format_error(response: ErrorResponse) -> str:
        """Format error response."""
        if response.language == "ar":
            text = f"❌ {response.message_ar}"
            if response.suggestion:
                text += f"\n\n💡 {response.suggestion}"
        else:
            text = f"❌ {response.message}"
            if response.suggestion:
                text += f"\n\n💡 {response.suggestion}"
        return text


# Singleton instances
_output_builder: Optional[StructuredOutputBuilder] = None
_duplicate_detector: Optional[DuplicateDetector] = None
_response_formatter: Optional[ResponseFormatter] = None


def get_output_builder() -> StructuredOutputBuilder:
    """Get the StructuredOutputBuilder singleton."""
    global _output_builder
    if _output_builder is None:
        _output_builder = StructuredOutputBuilder()
    return _output_builder


def get_duplicate_detector() -> DuplicateDetector:
    """Get the DuplicateDetector singleton."""
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector()
    return _duplicate_detector


def get_response_formatter() -> ResponseFormatter:
    """Get the ResponseFormatter singleton."""
    global _response_formatter
    if _response_formatter is None:
        _response_formatter = ResponseFormatter()
    return _response_formatter
