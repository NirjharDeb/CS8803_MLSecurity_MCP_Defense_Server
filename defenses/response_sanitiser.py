"""Remove hidden payloads from tool responses."""

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

BASE64_BLOCK_REGEX = re.compile(
    r'(?:[A-Za-z0-9+/]{20,})={0,2}'
)

HTML_COMMENT_REGEX = re.compile(r"<!--.*?-->", re.DOTALL)

def sanitise_response_text(text: str, tool_name: str = "unknown") -> Tuple[str, bool]:
    """
    Detect and remove HTML comments and Base64-like payloads.
    
    Args:
        text: Text to sanitize
        tool_name: Name of tool that produced the text
    
    Returns:
        (sanitised_text, was_sanitised): Clean text and whether sanitization occurred
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

    text = _log_and_strip(HTML_COMMENT_REGEX, "HTML_COMMENT", text)
    text = _log_and_strip(BASE64_BLOCK_REGEX, "BASE64", text)

    return text, was_sanitised


def sanitise_content_block(block_text: str, tool_name: str) -> str:
    """
    Sanitize a content block from tool response.
    
    Args:
        block_text: Text to sanitize
        tool_name: Name of tool that produced the text
    
    Returns:
        Sanitized text
    """
    clean_text, _ = sanitise_response_text(block_text, tool_name)
    return clean_text


if __name__ == "__main__":
    """Interactive testing mode for sanitizer."""
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
