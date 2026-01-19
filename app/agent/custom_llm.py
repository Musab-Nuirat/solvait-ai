from typing import Any, List, Optional, Sequence
import asyncio

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    ChatResponseAsyncGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.custom import CustomLLM
from google import genai
from google.genai import types
import os


class GoogleGenaiLLM(CustomLLM):
    context_window: int = 32000
    num_output: int = 2048
    model_name: str = "gemini-2.0-flash-exp"
    api_key: str = None
    client: Any = None

    def __init__(self, model_name: str, api_key: str, **kwargs: Any):
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)
        self.client = genai.Client(api_key=api_key)

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    def _prepare_messages(self, messages: Sequence[ChatMessage]) -> tuple[str, list]:
        """Prepare system prompt and contents from messages."""
        system_prompt = ""
        contents = []
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            else:
                contents.append(
                    types.Content(
                        role="user" if msg.role == "user" else "model",
                        parts=[types.Part.from_text(text=msg.content)],
                    )
                )

        # If no user/assistant messages, add an empty user message to avoid API error
        if not contents:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="")],
                )
            )

        return system_prompt, contents

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        system_prompt, contents = self._prepare_messages(messages)

        # Safety settings to allow legitimate HR conversations (resignation, complaints, etc.)
        safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH"
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            safety_settings=safety_settings
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generate_content_config
        )

        return ChatResponse(message=ChatMessage(role="assistant", content=response.text))

    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        """Async chat implementation using thread pool."""
        return await asyncio.to_thread(self.chat, messages, **kwargs)

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return CompletionResponse(text=response.text)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        response = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt
        )
        for chunk in response:
            yield CompletionResponse(text=chunk.text, delta=chunk.text)

    @llm_chat_callback()
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        system_prompt, contents = self._prepare_messages(messages)

        generate_content_config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None
        )

        response = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=generate_content_config
        )

        for chunk in response:
            yield ChatResponse(
                message=ChatMessage(role="assistant", content=chunk.text),
                delta=chunk.text,
            )

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        """Async stream chat implementation."""

        async def gen() -> ChatResponseAsyncGen:
            for response in self.stream_chat(messages, **kwargs):
                yield response

        return gen()
