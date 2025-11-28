# middleware.py
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from defenses.alignment import is_tool_call_likely_aligned
from defenses.response_sanitiser import sanitise_content_block
from defenses.prompt_injection_detector import detect_injection_patterns, neutralize_injection_patterns
from defenses.response_framing import frame_external_content, compute_instruction_score
from defenses.dependency_tracker import record_tool_call, check_suspicious_sequence

class DefenseMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept every tool call going through the proxy.

        Defense Layers:
        1. Alignment check: Verify tool call matches user intent
        2. Dependency tracking: Detect suspicious tool call sequences
        3. Execute tool call
        4. Pattern detection: Scan response for prompt injection
        5. Response sanitization: Remove hidden payloads
        6. Response framing: Mark external content clearly
        """

        tool_name = getattr(context.message, "name", None) or ""
        arguments = getattr(context.message, "arguments", {}) or {}

        # === Layer 1: Alignment Check ===
        # Try to get the tool's description (best-effort; failures just mean we
        # fall back to name-only matching).
        tool_description = None
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(tool_name)
                tool_description = getattr(tool, "description", None)
            except Exception:
                # If we can't resolve metadata, just proceed with name-only.
                tool_description = None

        # Run the cheap heuristic alignment check
        allow, score = is_tool_call_likely_aligned(
            arguments=arguments,
            tool_name=tool_name,
            tool_description=tool_description,
        )

        if not allow:
            # Block the call before it hits the malicious MCP server.
            raise ToolError(
                f"Blocked tool '{tool_name}': it appears unrelated to the "
                f"current request (alignment score={score:.2f}). "
                "This may indicate an unsafe or unintended tool invocation."
            )

        # === Layer 2: Dependency Tracking ===
        # Check if this call creates a suspicious sequence
        is_suspicious_seq, reason = check_suspicious_sequence(tool_name)
        if is_suspicious_seq:
            raise ToolError(
                f"Blocked tool '{tool_name}': suspicious call sequence detected. {reason}"
            )

        # === Execute the tool ===
        result = await call_next(context)
        
        # Record this call for future dependency tracking
        record_tool_call(tool_name)

        # === Layer 3 & 4: Pattern Detection and Sanitization ===
        content = getattr(result, "content", None)
        if content:
            for block in content:
                if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                    block.text = self._process_response_text(block.text, tool_name)

        data = getattr(result, "data", None)
        if isinstance(data, str):
            result.data = self._process_response_text(data, tool_name)

        return result

    def _process_response_text(self, text: str, tool_name: str) -> str:
        """
        Process tool response text through all defense layers:
        1. Detect injection patterns
        2. Neutralize detected patterns
        3. Sanitize hidden payloads (base64, HTML comments)
        4. Frame external content with attribution
        5. Add verification stamp
        """
        if not text or not text.strip():
            return text

        # Detect injection patterns
        is_suspicious, matched_patterns = detect_injection_patterns(text)
        
        # Neutralize command-like patterns
        if is_suspicious:
            text = neutralize_injection_patterns(text)
        
        # Remove hidden payloads (existing sanitization)
        text = sanitise_content_block(text, tool_name)
        
        # Compute instruction score for additional context
        instruction_score = compute_instruction_score(text)
        high_instruction_score = instruction_score > 0.3
        
        # Frame the content if suspicious or highly directive
        if is_suspicious or high_instruction_score:
            detection_info = None
            if matched_patterns:
                detection_info = f"Matched patterns: {len(matched_patterns)}"
            if high_instruction_score:
                detection_info = (detection_info or "") + f" | Instruction score: {instruction_score:.2f}"
            
            text = frame_external_content(
                text,
                tool_name,
                is_suspicious=True,
                detection_info=detection_info
            )
        
        # Add verification stamp
        text = f"{text}\n\nThis has been verified by a lone Yellow Jacket!"
        
        return text
