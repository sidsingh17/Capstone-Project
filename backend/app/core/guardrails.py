import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

_BLOCKED_PATTERNS = [
    r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+instructions?\b",
    r"\bsystem\s+prompt\b",
    r"\bjailbreak\b",
    r"\bact\s+as\s+if\b",
    r"<script[^>]*>",
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|TRUNCATE)\s+\w+",
    r"\bexec(ute)?\s*\(",
    r"\b(rm|del)\s+-rf?\b",
]

_SUPPLY_CHAIN_KEYWORDS = [
    "supplier", "shipment", "delivery", "warehouse", "inventory", "logistics",
    "transport", "freight", "cargo", "port", "delay", "stockout", "procurement",
    "vendor", "distribution", "fulfillment", "supply chain", "disruption",
    "demand", "forecast", "risk", "incident", "order", "product", "route",
    "customs", "import", "export", "region", "cost", "capacity",
]

_MAX_QUERY_LENGTH = 1000
_MIN_QUERY_LENGTH = 3


def validate_query(query: str) -> Tuple[bool, str]:
    if not query or not query.strip():
        return False, "Query cannot be empty"

    if len(query) < _MIN_QUERY_LENGTH:
        return False, f"Query too short (minimum {_MIN_QUERY_LENGTH} characters)"

    if len(query) > _MAX_QUERY_LENGTH:
        return False, f"Query too long (maximum {_MAX_QUERY_LENGTH} characters)"

    query_lower = query.lower()
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.warning(f"Blocked query pattern detected: {pattern[:40]}")
            return False, "Query contains disallowed content"

    return True, ""


def is_supply_chain_relevant(query: str) -> Tuple[bool, float]:
    """Returns (is_relevant, confidence_score)."""
    query_lower = query.lower()
    matched = sum(1 for kw in _SUPPLY_CHAIN_KEYWORDS if kw in query_lower)
    confidence = min(matched / 3.0, 1.0)
    return confidence >= 0.33, confidence


def sanitize_query(query: str) -> str:
    query = query.strip()
    query = re.sub(r"\s+", " ", query)
    query = re.sub(r"[<>{}|\\^`]", "", query)
    return query
