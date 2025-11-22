# middleware.py
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from defenses.alignment import is_tool_call_likely_aligned
from defenses.response_sanitiser import sanitise_content_block

class DefenseMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept every tool call going through the proxy.

        1. Cheap heuristic: check whether the tool call seems aligned with the
           natural-language text in its arguments (if any).
        2. If it looks unrelated, block it and warn the caller.
        3. Otherwise, forward to the underlying MCP server and post-process
           the result (YellowJacket stamp).
        """

        tool_name = getattr(context.message, "name", None) or ""
        arguments = getattr(context.message, "arguments", {}) or {}

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
            # The message here can be tuned to whatever UX you want.
            raise ToolError(
                f"Blocked tool '{tool_name}': it appears unrelated to the "
                f"current request (alignment score={score:.2f}). "
                "This may indicate an unsafe or unintended tool invocation."
            )

        # === Normal execution path ===
        result = await call_next(context)

        # Placeholder for hidden-payload detection (currently just adds
        # "This has been verifed by a lone Yellow Jacket!" to the end of the content)
        content = getattr(result, "content", None)
        if content:
            for block in content:
                if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                    block.text = (
                        f"{sanitise_content_block(block.text, tool_name)} This has been verifed by a lone Yellow Jacket!"
                    )

        data = getattr(result, "data", None)
        if isinstance(data, str):
            result.data = (
                sanitise_content_block(data, tool_name) + " This has been verifed by a lone Yellow Jacket!"
            )

        return result
