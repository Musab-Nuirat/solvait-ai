"""Intent Router - Lightweight intent detection with focused prompts."""

from typing import Tuple, Optional
import re


class IntentRouter:
    """
    Lightweight intent detection before main agent.
    Routes to intent-specific prompts for better LLM compliance.
    """

    # Intent-specific prompts (smaller, focused)
    INTENT_PROMPTS = {
        "leave_balance": """You are checking leave balance.
RULES:
1. Call get_leave_balance tool
2. Display balances in a clear structured format
3. MANDATORY: End with "Would you like me to help you request a new leave now?" (or Arabic equivalent)
4. DO NOT skip the follow-up question!""",

        "leave_request": """You are processing a leave request.
RULES:
1. Gather: leave type, start date, end date (ASK if missing)
2. STEP 1 - PREVIEW: Call submit_leave_request with user_confirmed="no"
   - This returns a PREVIEW (not actual submission!)
   - Display the summary to user including balance impact
   - ASK: "Do you want to submit this request? (Yes/No)"
   - STOP AND WAIT for user response!
3. STEP 2 - SUBMIT: Only after user says yes/نعم/تمام, call submit_leave_request with user_confirmed="yes"
4. If conflict warning, inform user and ask to proceed
5. After submission, show remaining balance from the response
6. If user cancels, acknowledge cancellation

CRITICAL: First call must have user_confirmed="no" to get preview. Only set user_confirmed="yes" after user confirms!""",

        "payslip": """You are showing a payslip.
RULES - FOLLOW EXACTLY:
1. CRITICAL - Check if user's message contains keywords:
   - Latest keywords: "latest", "الأخير", "most recent", "الأحدث", "last"
   - Month names: January, February, March, April, May, June, July, August, September, October, November, December
   - Month names Arabic: يناير, فبراير, مارس, أبريل, مايو, يونيو, يوليو, أغسطس, سبتمبر, أكتوبر, نوفمبر, ديسمبر

2. IF USER MESSAGE HAS NO MONTH AND NO "LATEST" KEYWORD:
   - DO NOT call any payslip tool!
   - ASK: "Which month would you like to view? (e.g., January 2026, or 'latest' for most recent)"
   - STOP AND WAIT!

3. IF USER MESSAGE CONTAINS "LATEST" OR "الأخير":
   - Call get_latest_payslip (NOT get_payslip!)

4. IF USER MESSAGE CONTAINS A MONTH NAME:
   - Call get_payslip with month=<number>

5. Display ALL breakdown items
6. End with "Download option coming soon!" """,

        "excuse": """You are creating an excuse request.
RULES - FOLLOW EXACTLY:
1. Determine type: late_arrival OR early_departure
2. COLLECT ALL REQUIRED INFO BEFORE PROCEEDING:
   - For late_arrival: ASK "What time did you arrive?" (e.g., 8:30 AM)
   - For early_departure: ASK "What time did you leave?" (e.g., 3:00 PM)
   - MUST have SPECIFIC reason - ASK "What was the specific reason?" (generic like "traffic" alone is NOT accepted, need details like "traffic jam on highway due to accident")
3. DO NOT call create_excuse until you have ALL: type, time, AND detailed reason
4. TIME FORMAT: Accept AM/PM (e.g., "8:30 AM", "3pm") and 24-hour (e.g., "08:30", "15:00")
5. MANDATORY CONFIRMATION: After collecting all info, show summary:
   ```
   Excuse Request Summary:
   - Date: [date]
   - Type: Late Arrival / Early Departure
   - Time: [time]
   - Reason: [reason]

   Do you want to submit this excuse? (Yes/No)
   ```
6. WAIT for explicit "yes" or "نعم" before calling create_excuse
7. If user cancels, acknowledge cancellation""",

        "policy": """You are answering an HR policy question.
RULES:
1. ALWAYS call hr_policy_search first
2. Quote the specific policy section in your answer
3. If not found, suggest contacting HR""",

        "cancel": """The user wants to cancel.
RESPONSE: "No problem! The request has been cancelled. How else can I help you?"
Arabic: "لا مشكلة! تم إلغاء الطلب. كيف يمكنني مساعدتك؟" """,

        "greeting": """The user is greeting you.
RULES:
1. Respond warmly and professionally
2. Offer to help with HR matters
3. Keep it brief""",

        "general": """You are handling a general HR query.
RULES:
1. Be helpful and professional
2. Use appropriate tools
3. If unclear, ask for clarification"""
    }

    # Intent detection keywords
    INTENT_KEYWORDS = {
        "leave_balance": [
            "balance", "رصيد", "how many days", "كم يوم", "remaining", "متبقي",
            "check leave", "leave balance", "رصيد اجازات", "رصيد الاجازات"
        ],
        "leave_request": [
            "want leave", "request leave", "take leave", "need leave",
            "اريد اجازة", "ابغى اجازة", "بدي اجازة", "طلب اجازة",
            "annual leave", "sick leave", "اجازة سنوية", "اجازة مرضية",
            "from", "to", "من", "الى", "tomorrow", "غدا", "next week"
        ],
        "payslip": [
            "payslip", "salary", "راتب", "قسيمة", "كشف راتب", "pay slip",
            "كشف الراتب", "رواتب", "معاش"
        ],
        "excuse": [
            "late", "early", "تأخر", "تأخرت", "متأخر", "excuse",
            "استئذان", "مغادرة", "arrived late", "left early",
            "وصلت متأخر", "غادرت مبكر"
        ],
        "policy": [
            "policy", "rule", "allowed", "سياسة", "قانون", "مسموح",
            "can i", "هل يمكن", "is it allowed", "what is the rule",
            "handbook", "دليل"
        ],
        "cancel": [
            "cancel", "stop", "abort", "never mind",
            "إلغاء", "توقف", "لا أريد", "خلاص", "الغاء", "كنسل"
        ],
        "greeting": [
            "hello", "hi", "hey", "مرحبا", "السلام", "اهلا", "صباح", "مساء"
        ]
    }

    def detect_intent(self, message: str, chat_history: Optional[list] = None) -> Tuple[str, str]:
        """
        Detect the user's intent from their message.

        Args:
            message: The user's message
            chat_history: Previous conversation messages

        Returns:
            Tuple of (intent_name, intent_prompt)
        """
        message_lower = message.lower().strip()

        # Check for cancel first (highest priority)
        if any(kw in message_lower for kw in self.INTENT_KEYWORDS["cancel"]):
            return "cancel", self.INTENT_PROMPTS["cancel"]

        # Score each intent based on keyword matches
        scores = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[intent] = score

        # Get current intent from message
        current_intent = max(scores, key=scores.get) if scores else None

        # Check for confirmation response (if in middle of a flow)
        if chat_history:
            confirm_keywords = ["yes", "yeah", "ok", "sure", "نعم", "اه", "تمام", "موافق", "بدي", "اكيد", "ايوه"]

            # Only treat as confirmation if NO other intent keywords detected
            if not current_intent and any(kw in message_lower for kw in confirm_keywords):
                # Check what we were doing before
                last_intent = self._get_last_intent(chat_history)
                if last_intent in ["leave_request", "excuse"]:
                    return last_intent, self.INTENT_PROMPTS[last_intent]

        # Return highest scoring intent
        if current_intent:
            prompt = self.INTENT_PROMPTS[current_intent]

            # Check if this is an INTENT CHANGE (different from previous)
            prev_intent = self._get_last_intent(chat_history) if chat_history else None
            if prev_intent and current_intent != prev_intent:
                # Intent changed - add isolation instruction to prompt
                isolation_note = f"\n\n## INTENT CHANGE DETECTED\nPrevious flow was: {prev_intent}. User is now asking about: {current_intent}.\nSTART FRESH - do NOT use any data from the previous flow."
                prompt += isolation_note

            # PAYSLIP SPECIAL CHECK: If payslip intent but no month/latest in message
            if current_intent == "payslip":
                latest_keywords = ["latest", "الأخير", "most recent", "الأحدث", "last", "الاخير"]
                month_keywords = ["january", "february", "march", "april", "may", "june", "july",
                                  "august", "september", "october", "november", "december",
                                  "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                                  "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
                                  "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

                has_latest = any(kw in message_lower for kw in latest_keywords)
                has_month = any(kw in message_lower for kw in month_keywords)

                if not has_latest and not has_month:
                    prompt += "\n\n## USER DID NOT SPECIFY MONTH\nThe user's message does NOT contain 'latest' or a month name.\nYOU MUST ASK which month they want to view. DO NOT call get_payslip with get_latest='yes'!"

            return current_intent, prompt

        # Default to general
        return "general", self.INTENT_PROMPTS["general"]

    def _get_last_intent(self, chat_history: list) -> Optional[str]:
        """Try to determine what intent we were handling before."""
        if not chat_history:
            return None

        # Look at recent messages for clues
        for msg in reversed(chat_history[-4:]):
            content = msg.get("content", "").lower()
            if "leave" in content or "اجازة" in content:
                return "leave_request"
            if "excuse" in content or "استئذان" in content or "تأخر" in content:
                return "excuse"
            if "payslip" in content or "راتب" in content:
                return "payslip"

        return None

    def get_combined_prompt(self, base_prompt: str, intent: str) -> str:
        """
        Combine base system prompt with intent-specific rules.

        Args:
            base_prompt: The base system prompt
            intent: The detected intent

        Returns:
            Combined prompt with intent-specific rules at the top
        """
        intent_prompt = self.INTENT_PROMPTS.get(intent, self.INTENT_PROMPTS["general"])

        combined = f"""## CURRENT TASK: {intent.upper().replace('_', ' ')}
{intent_prompt}

---

{base_prompt}"""

        return combined


class ToolOutputInterceptor:
    """
    Intercepts tool outputs to extract and enforce mandatory elements.
    Prevents the LLM from rephrasing or skipping important parts.
    """

    # Mandatory follow-ups that must appear in responses
    MANDATORY_FOLLOWUPS = {
        "get_leave_balance": {
            "en": "Would you like me to help you request a new leave now?",
            "ar": "هل تريد مساعدتك في طلب إجازة جديدة الآن؟"
        },
        "get_payslip": {
            "en": "Download option coming soon!",
            "ar": "خيار التحميل قريباً!"
        }
    }

    def intercept(self, tool_name: str, tool_output: str, is_arabic: bool = False) -> dict:
        """
        Intercept tool output and extract mandatory elements.

        Args:
            tool_name: Name of the tool that was called
            tool_output: The raw output from the tool
            is_arabic: Whether the conversation is in Arabic

        Returns:
            Dict with 'data' and optional 'mandatory_followup'
        """
        result = {
            "data": tool_output,
            "mandatory_followup": None,
            "display_instructions": None
        }

        # Check if this tool has mandatory follow-ups
        if tool_name in self.MANDATORY_FOLLOWUPS:
            lang = "ar" if is_arabic else "en"
            result["mandatory_followup"] = self.MANDATORY_FOLLOWUPS[tool_name][lang]

        # Add display instructions for specific tools
        if tool_name == "get_leave_balance":
            result["display_instructions"] = "Display as a clear list with remaining days for each leave type."

        if tool_name == "get_payslip":
            result["display_instructions"] = "Display ALL breakdown items. Do not summarize."

        return result

    def enforce_followup(self, response: str, followup: str) -> str:
        """
        Ensure the mandatory follow-up appears in the response.

        Args:
            response: The agent's response
            followup: The mandatory follow-up text

        Returns:
            Response with follow-up appended if missing
        """
        if not followup:
            return response

        # Check if similar follow-up already exists (in any language)
        followup_indicators = [
            "would you like", "do you want", "هل تريد", "هل تود", "هل ترغب",
            "request a new leave", "طلب إجازة جديدة", "مساعدتك في طلب",
            "download option", "خيار التحميل"
        ]

        response_lower = response.lower()
        already_has_followup = any(indicator in response_lower for indicator in followup_indicators)

        if not already_has_followup:
            # Append the follow-up only if not present
            response = response.rstrip() + "\n\n" + followup

        return response


# Singleton instances
_intent_router: Optional[IntentRouter] = None
_tool_interceptor: Optional[ToolOutputInterceptor] = None


def get_intent_router() -> IntentRouter:
    """Get or create the IntentRouter singleton."""
    global _intent_router
    if _intent_router is None:
        _intent_router = IntentRouter()
    return _intent_router


def get_tool_interceptor() -> ToolOutputInterceptor:
    """Get or create the ToolOutputInterceptor singleton."""
    global _tool_interceptor
    if _tool_interceptor is None:
        _tool_interceptor = ToolOutputInterceptor()
    return _tool_interceptor
