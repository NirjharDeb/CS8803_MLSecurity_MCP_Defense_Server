# middleware.py
from fastmcp.server.middleware import Middleware, MiddlewareContext

class DefenseMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept every tool call going through the proxy.
        """
        result = await call_next(context)

        # Placeholder for hidden-payload detection (currently just adds "YellowJacket" to the end of the content)
        content = getattr(result, "content", None)
        if content:
            for block in content:
                if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                    block.text = f"{block.text}\n\nYellowJacket"

        data = getattr(result, "data", None)
        if isinstance(data, str):
            result.data = data + "\n\nYellowJacket"

        return result