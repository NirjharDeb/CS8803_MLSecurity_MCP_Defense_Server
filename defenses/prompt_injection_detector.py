"""Detect and neutralize prompt injection patterns in tool responses."""

import re
from typing import List, Tuple

_AUTHORITY_PATTERNS = [
    r'\b(SYSTEM|CRITICAL|IMPORTANT|ADMIN|SECURITY ALERT|WARNING|ERROR)\s*:',
    r'\b(OVERRIDE|EMERGENCY|URGENT)\b',
]

_COMMAND_PATTERNS = [
    r'\b(you must|you should|you need to|do not|never tell|always respond)\b',
    r'\b(ignore previous|forget|from now on|your new role)\b',
    r'\b(tell the user|inform the user|say that|respond with)\b',
]

_TOOL_MANIPULATION_PATTERNS = [
    r'\b(call|invoke|use|execute)\s+\w+\s+(tool|function)',
    r'\btool_name\s*[=:]',
]

_FALSE_CLAIM_PATTERNS = [
    r'\b(security compromised|access denied|account locked|disabled|suspended)\b',
    r'\b(you cannot|you can\'t|unable to|forbidden)\b',
]


def _compile_patterns(pattern_lists: List[List[str]]) -> List[re.Pattern]:
    """Compile pattern lists into regex objects."""
    all_patterns = []
    for pattern_list in pattern_lists:
        all_patterns.extend(pattern_list)
    return [re.compile(p, re.IGNORECASE) for p in all_patterns]


_ALL_PATTERNS = _compile_patterns([
    _AUTHORITY_PATTERNS,
    _COMMAND_PATTERNS,
    _TOOL_MANIPULATION_PATTERNS,
    _FALSE_CLAIM_PATTERNS,
])


def detect_injection_patterns(text: str) -> Tuple[bool, List[str]]:
    """
    Scan text for prompt injection patterns.
    
    Args:
        text: Text to scan
    
    Returns:
        (is_suspicious, matched_patterns): Whether text is suspicious and which patterns matched
    """
    if not text or len(text.strip()) < 10:
        return False, []
    
    matched = []
    for pattern in _ALL_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
    
    is_suspicious = len(matched) >= 2
    
    return is_suspicious, matched


def neutralize_injection_patterns(text: str) -> str:
    """
    Neutralize injection patterns by wrapping them in quotes and attribution markers.
    
    Args:
        text: Text to neutralize
    
    Returns:
        Text with command-like patterns quoted to prevent LLM interpretation
    """
    if not text:
        return text
    
    result = text
    
    for pattern in _AUTHORITY_PATTERNS:
        result = re.sub(
            pattern,
            r'[Content claims: "\1":]',
            result,
            flags=re.IGNORECASE
        )
    
    for pattern in _COMMAND_PATTERNS:
        result = re.sub(
            pattern,
            r'["\1"]',
            result,
            flags=re.IGNORECASE
        )
    
    return result

