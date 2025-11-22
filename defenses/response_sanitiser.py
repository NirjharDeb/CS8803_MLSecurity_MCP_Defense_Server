# defenses/response_sanitiser.py
"""
Response Sanitiser
------------------
Silent response-layer defense that:
1. Detects Base64-like encoded segments and HTML comments in text
2. Removes them silently
3. Logs every sanitisation event to FastMCP server logs

Designed to be plugged into DefenseMiddleware as a post-processing
step for tool responses.
"""

import re
import logging
from typing import Tuple


logger = logging.getLogger("response_sanitiser")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [SANITISED] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Detects reasonably long base64-like sequences to reduce false positives
BASE64_BLOCK_REGEX = re.compile(
    r'(?:[A-Za-z0-9+/]{20,})={0,2}'
)

# Matches HTML comments: <!-- anything --> (non-greedy, multiline safe)
HTML_COMMENT_REGEX = re.compile(r"<!--.*?-->", re.DOTALL)

def sanitise_response_text(text: str, tool_name: str = "unknown") -> Tuple[str, bool]:
    """
    Detect and silently remove HTML comments and Base64-like payloads.
    All removals are logged in a generic format.

    Returns:
        (sanitised_text, was_sanitised)
    """

    was_sanitised = False

    def _log_and_strip(pattern, label, current_text):
        nonlocal was_sanitised
        matches = list(pattern.finditer(current_text))
        if not matches:
            return current_text

        for match in matches:
            payload = match.group(0)
            logger.info(
                f"Tool={tool_name} | Type={label} | Length={len(payload)} | Snippet={payload[:40]}..."
            )

        was_sanitised = True
        return pattern.sub('', current_text)

    # Apply sanitisation pipeline
    text = _log_and_strip(HTML_COMMENT_REGEX, "HTML_COMMENT", text)
    text = _log_and_strip(BASE64_BLOCK_REGEX, "BASE64", text)

    return text, was_sanitised


def sanitise_content_block(block_text: str, tool_name: str) -> str:
    """
    Wrapper to sanitise a content block safely.
    """
    clean_text, _ = sanitise_response_text(block_text, tool_name)
    return clean_text


if __name__ == "__main__":
    print("=== Response Sanitiser Interactive Mode ===")
    print("Type text to sanitise. Type 'exit' to quit.")

    while True:
        user_input = input("> ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Exiting test mode.")
            break

        cleaned, was_sanitised = sanitise_response_text(
            user_input,
            tool_name="manual_test"
        )

        print("Sanitised Output:")
        print(cleaned)
        print("Was Sanitised:", was_sanitised)
        print("-")
