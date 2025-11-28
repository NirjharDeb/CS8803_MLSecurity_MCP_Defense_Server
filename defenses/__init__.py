# defenses/__init__.py
"""
Defense modules for runtime MCP tool call protection.

Available defenses:
- alignment: Check tool call alignment with user intent
- response_sanitiser: Remove hidden payloads (base64, HTML comments)
- prompt_injection_detector: Detect and neutralize injection patterns
- response_framing: Frame external content with attribution markers
- dependency_tracker: Track tool call sequences for anomaly detection
"""

