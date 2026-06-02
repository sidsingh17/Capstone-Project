from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import logging
from openai import OpenAI

from app.core.config import get_settings, make_openai_client
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class BaseSupplyChainAgent(ABC):
    """Abstract base for all supply chain agents."""

    agent_name: str = "BaseAgent"
    agent_type: str = "base"

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = make_openai_client()
        return self._client

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent-specific system prompt."""
        ...

    @property
    @abstractmethod
    def tools(self) -> List[Dict[str, Any]]:
        """Tools available to this agent (OpenAI function-calling format)."""
        ...

    @abstractmethod
    def analyze(self, query: str, context: List[Dict[str, Any]], **kwargs) -> AgentResult:
        """Run the agent analysis and return structured results."""
        ...

    def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 1500,
    ) -> str:
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        kwargs: Dict[str, Any] = {
            "model": self.settings.LLM_MODEL,
            "max_tokens": max_tokens,
            "messages": full_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        # Handle tool calls if present
        if msg.tool_calls:
            tool_result_messages = [{"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls}]
            for tc in msg.tool_calls:
                result = self._handle_tool_call(
                    tc.function.name,
                    json.loads(tc.function.arguments),
                )
                tool_result_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

            kwargs["messages"] = full_messages + tool_result_messages
            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

        return msg.content or ""

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Override in subclasses to implement tool logic."""
        return f"Tool {tool_name} called with {tool_input}"

    def _build_context_summary(self, context: List[Dict[str, Any]], max_items: int = 5) -> str:
        parts = []
        for i, doc in enumerate(context[:max_items], 1):
            meta = doc.get("metadata", {})
            content = doc.get("content", "")[:300]
            parts.append(
                f"[{i}] {content}\n"
                f"    Supplier: {meta.get('supplier_id','?')} | "
                f"Severity: {meta.get('severity','?')} | "
                f"Delay: {meta.get('delivery_delay',0):.0f}d | "
                f"Inventory: {meta.get('inventory_level',0):.0f} units"
            )
        return "\n\n".join(parts)
