"""Debug tracer for RAG and agent processes."""

import json
from typing import Any, List, Optional
from datetime import datetime
from app.config import DEBUG_MODE


class Tracer:
    """
    Simple tracer to log RAG process, tool calls, and reasoning steps.
    Controlled by DEBUG_MODE in config.
    """

    def __init__(self, enabled: Optional[bool] = None):
        self.enabled = enabled if enabled is not None else DEBUG_MODE
        self.traces: List[dict] = []
        self.start_time = datetime.now()

    def log(self, category: str, message: str, data: Any = None):
        """Log a trace entry."""
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_ms": int((datetime.now() - self.start_time).total_seconds() * 1000),
            "category": category,
            "message": message,
        }
        if data is not None:
            entry["data"] = data

        self.traces.append(entry)
        self._print_trace(entry)

    def _print_trace(self, entry: dict):
        """Print trace to console with formatting."""
        elapsed = f"[{entry['elapsed_ms']:>5}ms]"
        category = f"[{entry['category']:^12}]"

        # Color codes for different categories
        colors = {
            "QUERY": "\033[94m",      # Blue
            "RETRIEVAL": "\033[92m",  # Green
            "CHUNKS": "\033[93m",     # Yellow
            "TOOL_CALL": "\033[95m",  # Magenta
            "TOOL_RESULT": "\033[96m", # Cyan
            "LLM": "\033[91m",        # Red
            "RESPONSE": "\033[97m",   # White
        }
        reset = "\033[0m"
        color = colors.get(entry["category"], "")

        print(f"{color}{elapsed} {category} {entry['message']}{reset}")

        if "data" in entry:
            data = entry["data"]
            if isinstance(data, str):
                # Truncate long strings
                if len(data) > 500:
                    data = data[:500] + "..."
                print(f"           └─ {data}")
            elif isinstance(data, list):
                for i, item in enumerate(data[:5]):  # Show max 5 items
                    prefix = "├─" if i < len(data) - 1 else "└─"
                    if isinstance(item, dict):
                        summary = json.dumps(item, ensure_ascii=False)[:200]
                        print(f"           {prefix} {summary}")
                    else:
                        print(f"           {prefix} {str(item)[:200]}")
                if len(data) > 5:
                    print(f"           └─ ... and {len(data) - 5} more items")
            elif isinstance(data, dict):
                summary = json.dumps(data, ensure_ascii=False, indent=2)[:500]
                for line in summary.split('\n'):
                    print(f"           {line}")

    def log_query(self, query: str):
        """Log incoming query."""
        self.log("QUERY", f"User query: {query[:100]}...")

    def log_retrieval(self, query: str, top_k: int):
        """Log retrieval start."""
        self.log("RETRIEVAL", f"Searching for top-{top_k} relevant chunks")

    def log_chunks(self, chunks: List[dict]):
        """Log retrieved chunks."""
        self.log("CHUNKS", f"Retrieved {len(chunks)} chunks", chunks)

    def log_chunks_detailed(self, chunks: List[dict]):
        """Log retrieved chunks with detailed source information."""
        if not self.enabled:
            return

        print(f"\n\033[93m{'='*60}")
        print(f"📚 RETRIEVED CHUNKS ({len(chunks)} results)")
        print(f"{'='*60}\033[0m")

        for chunk in chunks:
            rank = chunk.get("rank", "?")
            score = chunk.get("score", 0)
            source = chunk.get("source", "unknown")
            metadata = chunk.get("metadata", {})
            text_preview = chunk.get("text_preview", "")

            # Score color: green for high, yellow for medium, red for low
            if score >= 0.8:
                score_color = "\033[92m"  # Green
            elif score >= 0.5:
                score_color = "\033[93m"  # Yellow
            else:
                score_color = "\033[91m"  # Red

            print(f"\n\033[96m[Chunk #{rank}]\033[0m {score_color}Score: {score:.4f}\033[0m")
            print(f"  📄 Source: \033[95m{source}\033[0m")

            # Print all metadata
            if metadata:
                meta_items = []
                for key, value in metadata.items():
                    meta_items.append(f"{key}={value}")
                print(f"  🏷️  Metadata: {', '.join(meta_items)}")

            # Print text preview with proper formatting
            print(f"  📝 Text:")
            # Indent and wrap text preview
            wrapped_text = text_preview.replace('\n', '\n      ')
            print(f"      {wrapped_text}")

        print(f"\n\033[93m{'='*60}\033[0m\n")

    def log_tool_call(self, tool_name: str, args: dict):
        """Log tool invocation."""
        self.log("TOOL_CALL", f"Calling tool: {tool_name}", args)

    def log_tool_result(self, tool_name: str, result: Any):
        """Log tool result."""
        result_str = str(result)[:300] if result else "None"
        self.log("TOOL_RESULT", f"Result from {tool_name}", result_str)

    def log_llm(self, action: str, detail: str = ""):
        """Log LLM activity."""
        self.log("LLM", f"{action}: {detail[:100]}")

    def log_response(self, response: str):
        """Log final response."""
        self.log("RESPONSE", f"Final response generated ({len(response)} chars)")

    def get_traces(self) -> List[dict]:
        """Get all trace entries."""
        return self.traces

    def clear(self):
        """Clear traces and reset timer."""
        self.traces = []
        self.start_time = datetime.now()


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer(reset: bool = False) -> Tracer:
    """Get or create the global tracer instance."""
    global _tracer
    if _tracer is None or reset:
        _tracer = Tracer()
    return _tracer


def trace_enabled() -> bool:
    """Check if tracing is enabled."""
    return DEBUG_MODE
