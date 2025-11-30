"""Tool call alignment verification using token overlap heuristics."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import re

_STOPWORDS = {
    "the", "a", "an", "to", "of", "for", "and", "or", "in", "on", "with",
    "from", "by", "is", "are", "be", "this", "that", "it", "as", "at",
    "your", "you", "i", "we", "our", "us", "me"
}


@dataclass
class ToolCallContext:
    """Minimal view of a tool call for alignment checking."""
    candidate_text: Optional[str]
    tool_name: str
    tool_description: Optional[str]
    arguments: Dict[str, Any]


def _normalize(text: str) -> set[str]:
    """Lowercase, tokenize, and filter stopwords."""
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return {
        t
        for t in tokens
        if len(t) > 2 and t not in _STOPWORDS
    }


def _extract_candidate_text(arguments: Dict[str, Any]) -> Optional[str]:
    """
    Extract user prompt from tool arguments using heuristics.
    
    Args:
        arguments: Tool call arguments
    
    Returns:
        Longest natural-language string that looks like user intent
    """
    skip_keys = {"body", "content", "data", "payload", "html", "text"}
    
    candidates: list[str] = []

    for key, value in arguments.items():
        if isinstance(value, str) and key.lower() not in skip_keys:
            text = value.strip()
            if len(text) >= 20 and " " in text:
                candidates.append(text)

    if not candidates:
        return None

    candidates.sort(key=len, reverse=True)
    return candidates[0]


def compute_alignment_score(ctx: ToolCallContext) -> float:
    """
    Compute token overlap score between user text and tool metadata.
    
    Args:
        ctx: Tool call context
    
    Returns:
        Score in [0, 1] where higher means more aligned
    """
    if not ctx.candidate_text:
        return 1.0

    prompt_tokens = _normalize(ctx.candidate_text)
    if not prompt_tokens:
        return 1.0

    tool_text_parts = [ctx.tool_name or ""]
    if ctx.tool_description:
        tool_text_parts.append(ctx.tool_description)

    tool_text = " ".join(tool_text_parts)
    tool_tokens = _normalize(tool_text)

    if not tool_tokens:
        return 0.0

    overlap = prompt_tokens & tool_tokens
    return len(overlap) / float(len(prompt_tokens))


def is_tool_call_likely_aligned(
    arguments: Dict[str, Any],
    tool_name: str,
    tool_description: Optional[str],
    threshold: float = 0.12,
) -> Tuple[bool, float]:
    """
    Check if tool call matches user intent using token overlap.
    
    Args:
        arguments: Tool call arguments
        tool_name: Name of the tool
        tool_description: Tool description if available
        threshold: Minimum alignment score to allow
    
    Returns:
        (allowed, score): Whether call is allowed and its alignment score
    """
    candidate = _extract_candidate_text(arguments)
    ctx = ToolCallContext(
        candidate_text=candidate,
        tool_name=tool_name,
        tool_description=tool_description,
        arguments=arguments,
    )
    score = compute_alignment_score(ctx)

    if candidate is None:
        return True, score

    allow = score >= threshold
    return allow, score
