# defenses/alignment.py
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import re

# Very small, hardcoded stopword set to avoid matching on noise like "the", "your", etc.
_STOPWORDS = {
    "the", "a", "an", "to", "of", "for", "and", "or", "in", "on", "with",
    "from", "by", "is", "are", "be", "this", "that", "it", "as", "at",
    "your", "you", "i", "we", "our", "us", "me"
}


@dataclass
class ToolCallContext:
    """
    Minimal view of a tool call for alignment checking.
    """
    # "User-like" natural language text
    candidate_text: Optional[str]
    tool_name: str
    tool_description: Optional[str]
    arguments: Dict[str, Any]


def _normalize(text: str) -> set[str]:
    """
    Lowercase + simple tokenization + tiny stopword filter.
    """
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return {
        t
        for t in tokens
        if len(t) > 2 and t not in _STOPWORDS
    }


def _extract_candidate_text(arguments: Dict[str, Any]) -> Optional[str]:
    """
    Very cheap heuristic to find something that looks like a user prompt
    within the tool's arguments:

    - Take string-valued arguments.
    - Keep ones that are reasonably long and contain spaces.
    - Return the longest one (often the main "content"/"prompt"/"query").
    """
    candidates: list[str] = []

    for value in arguments.values():
        if isinstance(value, str):
            text = value.strip()
            # Heuristics: longish and multi-word looks more like natural language
            if len(text) >= 20 and " " in text:
                candidates.append(text)

    if not candidates:
        return None

    # Prefer the longest candidate as the main text
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def compute_alignment_score(ctx: ToolCallContext) -> float:
    """
    Compute a simple overlap score between the candidate text and the
    tool's name + description.

    Score = |overlap(prompt_tokens, tool_tokens)| / max(1, |prompt_tokens|)

    Returns a number in [0, 1]. Higher = more aligned.
    """
    if not ctx.candidate_text:
        # No text to compare; treat as "unknown" alignment.
        return 1.0

    prompt_tokens = _normalize(ctx.candidate_text)
    if not prompt_tokens:
        return 1.0  # nothing to compare, so don't block

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
    Cheap heuristic:
    - Extract candidate natural-language text from arguments.
    - Compute overlap score vs tool name+description.
    - If score < threshold, treat as suspicious/unrelated.

    Returns (allowed, score).
    """
    candidate = _extract_candidate_text(arguments)
    ctx = ToolCallContext(
        candidate_text=candidate,
        tool_name=tool_name,
        tool_description=tool_description,
        arguments=arguments,
    )
    score = compute_alignment_score(ctx)

    # If we have no candidate text, don't block; we simply can't judge.
    if candidate is None:
        return True, score

    # If overlap is very low, call looks unrelated.
    allow = score >= threshold
    return allow, score
