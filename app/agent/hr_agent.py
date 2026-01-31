"""LlamaIndex HR Agent - The Brain of Solvait AI Assistant."""

import asyncio
from typing import Optional, List
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool, FunctionTool
from app.agent.custom_llm import GoogleGenaiLLM

from app.config import GOOGLE_API_KEY, LLM_MODEL, DEBUG_MODE
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.intent_router import get_intent_router, get_tool_interceptor
from app.mcp.tools import get_hr_tools
from app.rag.policy_engine import get_policy_engine
from app.utils.tracer import get_tracer, Tracer


class HRAgent:
    """
    The main HR Agent that orchestrates:
    - Policy RAG queries
    - MCP tool execution
    - Bilingual responses
    """

    def __init__(self, employee_id: Optional[str] = None):
        """
        Initialize the HR Agent.

        Args:
            employee_id: The current user's employee ID for context
        """
        self.employee_id = employee_id or "EMP001"  # Default for demo

        # Initialize LLM
        self.llm = GoogleGenaiLLM(
            model_name=LLM_MODEL,
            api_key=GOOGLE_API_KEY,
        )

        # Get tools
        self.tools = self._build_tools()

        # Build the agent
        self.agent = ReActAgent(
            tools=self.tools,
            llm=self.llm,
            system_prompt=self._build_system_prompt(),
            verbose=True,  # Show reasoning for demo
            streaming=False,  # Disable streaming for complete responses
        )

    def _build_tools(self) -> List[BaseTool]:
        """Build the complete tool set for the agent."""
        tools = []

        # Add MCP tools (HR operations)
        tools.extend(get_hr_tools())

        # Add RAG tool (policy search)
        policy_engine = get_policy_engine()
        tools.append(policy_engine.get_tool())

        return tools

    def _build_system_prompt(self) -> str:
        """Build the system prompt with employee context and current date."""
        from datetime import date

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        today_ar = today.strftime("%d/%m/%Y")

        context = f"\n\n## 📅 TODAY'S DATE (CRITICAL CONTEXT)\n"
        context += f"- Current Date: **{today_str}** (Arabic: {today_ar})\n"
        context += f"- Day of Week: {today.strftime('%A')}\n"
        context += f"- ⚠️ RULE: When user says 'today', 'اليوم', or doesn't specify a date, YOU MUST USE **{today_str}**.\n"
        context += f"- ❌ DO NOT ask the user for the date if they imply today. Use the date above.\n"
        context += f"- ❌ DO NOT hallucinate old dates like 2024. Today is **{today_str}** (Year 2026).\n"
        context += f"- For 'tomorrow' / 'غداً', use {(today + __import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')}\n"

        context += f"\n## 👤 Current User Context\n"
        context += f"- The current user's Employee ID is: **{self.employee_id}**\n"
        context += f"- When the user says 'my', 'me', or 'I', they refer to employee {self.employee_id}\n"
        context += f"- ALWAYS use '{self.employee_id}' as the employee_id parameter when calling tools for this user\n"
        context += f"- DO NOT ask the user for their employee ID - you already know it is {self.employee_id}\n"

        return SYSTEM_PROMPT + context

    async def chat_async(
        self,
        message: str,
        chat_history: Optional[List[dict]] = None,
        return_traces: bool = False
    ) -> dict:
        """
        Process a user message asynchronously and return a response.

        Args:
            message: User's message in Arabic or English
            chat_history: Previous messages [{"role": "user/assistant", "content": "..."}]
            return_traces: If True, return traces along with response

        Returns:
            Dict with 'response' and optionally 'traces'
        """
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        # Reset tracer for new conversation
        tracer = get_tracer(reset=True)
        tracer.log_query(message)

        # PRE-PROCESSING: Handle special commands before agent
        message_lower = message.lower().strip()

        # Cancel keywords
        cancel_keywords = ["cancel", "stop", "abort", "never mind", "nevermind",
                          "إلغاء", "توقف", "لا أريد", "خلاص", "الغاء", "كنسل"]

        if any(keyword in message_lower for keyword in cancel_keywords):
            is_arabic = any(ord(c) > 127 for c in message)
            if is_arabic:
                response = "لا مشكلة! تم إلغاء الطلب. كيف يمكنني مساعدتك؟"
            else:
                response = "No problem! The request has been cancelled. How else can I help you?"
            tracer.log("CANCEL", "User cancelled current operation")
            output = {"response": response}
            if return_traces:
                output["traces"] = tracer.get_traces()
            return output

        # Confirmation keywords - check if previous message was asking for confirmation
        confirm_keywords = ["yes", "yeah", "yep", "ok", "okay", "sure", "proceed", "submit", "confirm",
                           "نعم", "اه", "ايوه", "اي", "تمام", "موافق", "اوك", "اكيد", "بدي", "ماشي"]

        # Check if this looks like a confirmation response
        if chat_history and len(chat_history) > 0:
            last_assistant_msg = ""
            for msg in reversed(chat_history):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg.get("content", "").lower()
                    break

            # If last message asked for confirmation and user is confirming
            confirmation_phrases = ["yes/no", "نعم/لا", "do you want to submit", "هل تريد تقديم",
                                   "do you want to proceed", "هل تريد المتابعة"]

            is_asking_confirmation = any(phrase in last_assistant_msg for phrase in confirmation_phrases)
            is_user_confirming = any(kw in message_lower for kw in confirm_keywords)

            if is_asking_confirmation and is_user_confirming:
                # Inject confirmation context into the message
                tracer.log("CONFIRM", "User confirmed previous request")
                message = f"[USER CONFIRMED: The user said '{message}' to confirm the previous request. PROCEED with the submission NOW. Do NOT ask for confirmation again.]"

        # INTENT DETECTION: Route to intent-specific prompt
        intent_router = get_intent_router()
        detected_intent, intent_prompt = intent_router.detect_intent(message, chat_history)
        tracer.log("INTENT", f"Detected intent: {detected_intent}")

        try:
            # Build chat history for context
            history_messages = []
            if chat_history:
                for msg in chat_history:
                    role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    history_messages.append(ChatMessage(role=role, content=msg["content"]))
                tracer.log("HISTORY", f"Loaded {len(history_messages)} previous messages")

            # Inject employee context AND DATE into message to ensure agent uses correct ID and Date
            from datetime import date
            
            # Detect language of CURRENT message only
            def detect_language(text: str) -> str:
                """Detect if text is Arabic or English based on character set."""
                arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأإؤئ')
                has_arabic = any(char in arabic_chars for char in text)
                # Count Arabic vs Latin characters
                arabic_count = sum(1 for char in text if char in arabic_chars)
                latin_count = sum(1 for char in text if char.isalpha() and ord(char) < 128)
                
                if arabic_count > 0 and arabic_count >= latin_count:
                    return "Arabic"
                elif latin_count > 0:
                    return "English"
                else:
                    return "Arabic" if has_arabic else "English"
            
            detected_lang = detect_language(message)
            today_str = date.today().strftime("%Y-%m-%d")
            context_prefix = f"""[SYSTEM CONTEXT]
- Current Date: {today_str} (Use this for 'today')
- Current Employee: {self.employee_id}
- Detected Language of CURRENT message: {detected_lang}
- CRITICAL: You MUST reply in {detected_lang}. Ignore the language of previous messages in chat history.
- Rule: Do NOT ask for the date.
[END SYSTEM CONTEXT]

"""
            augmented_message = context_prefix + message

            tracer.log_llm("ReActAgent", f"Starting reasoning loop (intent: {detected_intent})")

            # Build intent-aware system prompt
            intent_system_prompt = f"""## CURRENT TASK: {detected_intent.upper().replace('_', ' ')}
{intent_prompt}

---

""" + self._build_system_prompt()

            # Create a new agent with intent-specific prompt for this request
            intent_agent = ReActAgent(
                tools=self.tools,
                llm=self.llm,
                system_prompt=intent_system_prompt,
                verbose=True,
                streaming=False,
            )

            # Run agent with chat history
            handler = intent_agent.run(
                user_msg=augmented_message,
                chat_history=history_messages if history_messages else None
            )
            result = await handler

            # Log tool calls if any
            tool_names_called = []
            if result.tool_calls:
                for tc in result.tool_calls:
                    tracer.log_tool_call(tc.tool_name, {"args": str(tc.tool_kwargs)[:200]})
                    tool_names_called.append(tc.tool_name)

            response_content = result.response.content

            # POST-PROCESSING: Enforce mandatory follow-ups
            tool_interceptor = get_tool_interceptor()
            is_arabic = any(ord(c) > 127 for c in message)

            for tool_name in tool_names_called:
                intercepted = tool_interceptor.intercept(tool_name, "", is_arabic)
                if intercepted.get("mandatory_followup"):
                    response_content = tool_interceptor.enforce_followup(
                        response_content,
                        intercepted["mandatory_followup"]
                    )

            tracer.log_response(response_content)

            output = {"response": response_content}
            if return_traces and DEBUG_MODE:
                output["traces"] = tracer.get_traces()

            return output

        except Exception as e:
            error_msg = f"عذراً، حدث خطأ أثناء معالجة طلبك. / Sorry, an error occurred: {str(e)}"
            tracer.log("ERROR", str(e))
            output = {"response": error_msg}
            if return_traces and DEBUG_MODE:
                output["traces"] = tracer.get_traces()
            return output

    def chat(self, message: str) -> str:
        """
        Process a user message and return a response (sync wrapper).

        Args:
            message: User's message in Arabic or English

        Returns:
            Agent's response in the same language
        """
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create a new thread to run
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.chat_async(message))
                    return future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run directly
                return asyncio.run(self.chat_async(message))
        except Exception as e:
            error_msg = f"عذراً، حدث خطأ أثناء معالجة طلبك. / Sorry, an error occurred: {str(e)}"
            return error_msg

    def chat_with_history(self, message: str, history: Optional[List[dict]] = None) -> dict:
        """
        Process a message with conversation history.

        Args:
            message: Current user message
            history: List of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"response": str, "reasoning": List[str]} for Streamlit display
        """
        # For now, just use the simple chat
        # In production, we'd maintain conversation memory
        response = self.chat(message)

        # Extract reasoning steps from verbose output if available
        reasoning = []
        if hasattr(self.agent, '_current_reasoning'):
            reasoning = self.agent._current_reasoning

        return {
            "response": response,
            "reasoning": reasoning
        }


# Singleton for reuse
_hr_agent: Optional[HRAgent] = None


def get_hr_agent(employee_id: Optional[str] = None) -> HRAgent:
    """Get or create the HR Agent singleton."""
    global _hr_agent
    if _hr_agent is None or employee_id != _hr_agent.employee_id:
        _hr_agent = HRAgent(employee_id)
    return _hr_agent
