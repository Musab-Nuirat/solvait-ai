"""LlamaIndex HR Agent - The Brain of PeopleHub AI Assistant."""

import asyncio
from typing import Optional, List
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool, FunctionTool
from app.agent.custom_llm import GoogleGenaiLLM

from app.config import GOOGLE_API_KEY, LLM_MODEL, DEBUG_MODE
from app.agent.prompts import SYSTEM_PROMPT
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
        """Build the system prompt with employee context."""
        context = f"\n\n## 👤 Current User Context\n"
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

        try:
            # Build chat history for context
            history_messages = []
            if chat_history:
                for msg in chat_history:
                    role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    history_messages.append(ChatMessage(role=role, content=msg["content"]))
                tracer.log("HISTORY", f"Loaded {len(history_messages)} previous messages")

            # Inject employee context into message to ensure agent uses correct ID
            context_prefix = f"[Context: Current user is employee {self.employee_id}. Use this ID for all tool calls.]\n\n"
            augmented_message = context_prefix + message

            tracer.log_llm("ReActAgent", "Starting reasoning loop")

            # Run agent with chat history
            handler = self.agent.run(
                user_msg=augmented_message,
                chat_history=history_messages if history_messages else None
            )
            result = await handler

            # Log tool calls if any
            if result.tool_calls:
                for tc in result.tool_calls:
                    tracer.log_tool_call(tc.tool_name, {"args": str(tc.tool_kwargs)[:200]})

            response_content = result.response.content
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
