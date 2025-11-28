# defenses/prompt_injection_detector.py
import re
from typing import List, Tuple

# Patterns that indicate potential prompt injection attempts
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
    """Compile all pattern lists into regex objects."""
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
    Scan text for patterns that indicate prompt injection attempts.
    
    Returns:
        (is_suspicious, matched_patterns): A tuple where is_suspicious is True
        if injection patterns are detected, and matched_patterns contains the
        patterns that matched.
    """
    if not text or len(text.strip()) < 10:
        return False, []
    
    matched = []
    for pattern in _ALL_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
    
    # Consider suspicious if multiple patterns match or text is very directive
    is_suspicious = len(matched) >= 2
    
    return is_suspicious, matched


def neutralize_injection_patterns(text: str) -> str:
    """
    Neutralize detected injection patterns by wrapping them in quotes
    and adding attribution markers.
    
    This makes command-like text appear as quoted content rather than
    instructions to the LLM.
    """
    if not text:
        return text
    
    result = text
    
    # Replace authority claims with neutral attribution
    for pattern in _AUTHORITY_PATTERNS:
        result = re.sub(
            pattern,
            r'[Content claims: "\1":]',
            result,
            flags=re.IGNORECASE
        )
    
    # Neutralize direct commands by quoting them
    for pattern in _COMMAND_PATTERNS:
        result = re.sub(
            pattern,
            r'["\1"]',
            result,
            flags=re.IGNORECASE
        )
    
    return result

