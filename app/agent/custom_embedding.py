from typing import Any, List, Optional
from llama_index.core.base.embeddings.base import BaseEmbedding
from google import genai
from app.config import GOOGLE_API_KEY

class GoogleGenaiEmbedding(BaseEmbedding):
    model_name: str = "models/embedding-001"
    api_key: str = None
    client: Any = None

    def __init__(self, model_name: str = "models/embedding-001", api_key: str = None, **kwargs: Any):
        super().__init__(model_name=model_name, **kwargs)
        self.api_key = api_key or GOOGLE_API_KEY
        self.client = genai.Client(api_key=self.api_key)

    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding."""
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=query,
            config={"task_type": "RETRIEVAL_QUERY"}
        )
        return response.embeddings[0].values

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
            config={"task_type": "RETRIEVAL_DOCUMENT"}
        )
        return response.embeddings[0].values

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get text embeddings in batch."""
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config={"task_type": "RETRIEVAL_DOCUMENT"}
        )
        return [e.values for e in response.embeddings]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Get query embedding async."""
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Get text embedding async."""
        return self._get_text_embedding(text)
