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
2. Display balances clearly
3. MANDATORY: End with "Would you like me to help you request a new leave now?" (or Arabic equivalent)
4. DO NOT skip the follow-up question!""",

        "leave_request": """You are processing a leave request.
RULES:
1. Gather: leave type, start date, end date (ASK if missing)
2. Call get_leave_balance to check and INFORM user of balance impact
3. Call submit_leave_request - if conflict warning, inform user and ask to proceed
4. After submission, show confirmation with request ID
5. If user cancels, acknowledge cancellation""",

        "payslip": """You are showing a payslip.
RULES:
1. Call get_payslip tool
2. Display ALL breakdown items (basic, each allowance, each deduction)
3. MANDATORY: End with "Download option coming soon!"
4. DO NOT summarize - show full details""",

        "excuse": """You are creating an excuse request.
RULES:
1. For late_arrival: MUST have arrival time - ASK if missing
2. For early_departure: MUST have departure time - ASK if missing
3. MUST have specific reason - ASK if missing (generic reasons not accepted)
4. After collecting ALL info, create the excuse
5. If user cancels, acknowledge cancellation""",

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

        # Check for confirmation response (if in middle of a flow)
        if chat_history:
            confirm_keywords = ["yes", "yeah", "ok", "sure", "نعم", "اه", "تمام", "موافق", "بدي"]
            if any(kw in message_lower for kw in confirm_keywords):
                # Check what we were doing before
                last_intent = self._get_last_intent(chat_history)
                if last_intent in ["leave_request", "excuse"]:
                    return last_intent, self.INTENT_PROMPTS[last_intent]

        # Score each intent based on keyword matches
        scores = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[intent] = score

        # Return highest scoring intent
        if scores:
            best_intent = max(scores, key=scores.get)
            return best_intent, self.INTENT_PROMPTS[best_intent]

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
