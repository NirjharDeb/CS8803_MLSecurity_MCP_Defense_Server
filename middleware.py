"""Defense middleware for intercepting and securing MCP tool calls."""

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from defenses.alignment import is_tool_call_likely_aligned
from defenses.response_sanitiser import sanitise_content_block
from defenses.prompt_injection_detector import detect_injection_patterns, neutralize_injection_patterns
from defenses.response_framing import frame_external_content, compute_instruction_score
from defenses.dependency_tracker import record_tool_call, check_suspicious_sequence

class DefenseMiddleware(Middleware):
    """Multi-layered defense middleware for MCP tool call protection."""
    
    @staticmethod
    def _add_ronin_stamp(text: str) -> str:
        """Add Ronin verification stamp to text."""
        verification_stamp = (
            "\n\n"
            "⛩️ 検証済み ─ Verified by Ronin ─ 浪人 ⛩️"
        )
        return f"{text}{verification_stamp}"
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept tool calls and apply defense layers before and after execution.
        
        Args:
            context: Middleware context containing tool call details
            call_next: Function to execute the actual tool call
        
        Returns:
            Tool result after applying all defense layers
        """
        tool_name = getattr(context.message, "name", None) or ""
        arguments = getattr(context.message, "arguments", {}) or {}

        tool_description = None
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(tool_name)
                tool_description = getattr(tool, "description", None)
            except Exception:
                tool_description = None

        allow, score = is_tool_call_likely_aligned(
            arguments=arguments,
            tool_name=tool_name,
            tool_description=tool_description,
        )

        if not allow:
            error_msg = (
                f"Blocked tool '{tool_name}': it appears unrelated to the "
                f"current request (alignment score={score:.2f}). "
                "This may indicate an unsafe or unintended tool invocation."
            )
            raise ToolError(self._add_ronin_stamp(error_msg))

        is_suspicious_seq, reason = check_suspicious_sequence(tool_name)
        if is_suspicious_seq:
            error_msg = f"Blocked tool '{tool_name}': suspicious call sequence detected. {reason}"
            raise ToolError(self._add_ronin_stamp(error_msg))

        result = await call_next(context)
        record_tool_call(tool_name)

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
        Apply response-layer defenses to tool output.
        
        Args:
            text: Raw text from tool response
            tool_name: Name of the tool that generated the response
        
        Returns:
            Sanitized and framed text with verification stamp
        """
        if not text or not text.strip():
            return text

        is_suspicious, matched_patterns = detect_injection_patterns(text)
        
        if is_suspicious:
            text = neutralize_injection_patterns(text)
        
        text = sanitise_content_block(text, tool_name)
        
        instruction_score = compute_instruction_score(text)
        high_instruction_score = instruction_score > 0.3
        
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
        
        return self._add_ronin_stamp(text)
