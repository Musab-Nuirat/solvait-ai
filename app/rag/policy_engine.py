"""Policy Engine - RAG Query Engine for HR policies."""

from typing import Optional, List
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.core.schema import NodeWithScore

from app.rag.ingestion import DocumentIngestion
from app.agent.custom_llm import GoogleGenaiLLM
from app.config import GOOGLE_API_KEY, LLM_MODEL, DEBUG_MODE
from app.utils.tracer import get_tracer


class PolicyEngine:
    """RAG Query Engine for HR policy documents."""

    def __init__(self, index: Optional[VectorStoreIndex] = None):
        """
        Initialize the policy engine.

        Args:
            index: Pre-built VectorStoreIndex. If None, will load from ChromaDB or create sample.
        """
        if index:
            self.index = index
        else:
            # Try to load existing index or create sample
            ingestion = DocumentIngestion()
            self.index = ingestion.ingest_manuals()

        # Create retriever with top-k=5 for better coverage
        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=5
        )

        # Use our custom Gemini LLM for response synthesis
        self.llm = GoogleGenaiLLM(
            model_name=LLM_MODEL,
            api_key=GOOGLE_API_KEY,
        )

        # Create query engine with our LLM
        self.query_engine = RetrieverQueryEngine.from_args(
            retriever=self.retriever,
            llm=self.llm,
            verbose=True
        )
    
    def query(self, question: str) -> str:
        """
        Query the policy documents.

        Args:
            question: User's question about HR policies

        Returns:
            Answer grounded in the policy documents
        """
        tracer = get_tracer()
        tracer.log_retrieval(question, self.retriever.similarity_top_k)

        # First retrieve nodes to log them
        nodes = self.retriever.retrieve(question)

        # Log retrieved chunks with full metadata
        chunks_data = []
        for i, node in enumerate(nodes):
            # Build comprehensive chunk info with all metadata
            chunk_info = {
                "rank": i + 1,
                "score": round(node.score, 4) if node.score else 0,
                "source": node.metadata.get("source", "unknown"),
                "metadata": {k: v for k, v in node.metadata.items() if k != "source"},
                "text_preview": node.text[:150] + "..." if len(node.text) > 150 else node.text
            }
            chunks_data.append(chunk_info)

        tracer.log_chunks_detailed(chunks_data)

        # Now query with the engine
        response = self.query_engine.query(question)
        return str(response)
    
    def get_tool(self) -> FunctionTool:
        """Get this engine as a LlamaIndex FunctionTool for the agent."""
        def hr_policy_search(query: str) -> str:
            """
            Search HR policies and Employee Handbook for answers.

            Use this tool to search and answer questions about HR policies,
            company rules, leave policies, salary structure, overtime rules,
            health insurance coverage, attendance policies, and any other
            information from the Employee Handbook.

            Args:
                query: The question or search query about HR policies

            Returns:
                Answer based on the HR policy documents
            """
            return self.query(query)

        return FunctionTool.from_defaults(
            fn=hr_policy_search,
            name="hr_policy_search",
            description=(
                "Search HR policies and Employee Handbook for answers about "
                "leave policies, salary structure, overtime rules, health insurance, "
                "attendance policies, and company rules. Always cite sections."
            )
        )


# Singleton instance for reuse
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the policy engine singleton."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
