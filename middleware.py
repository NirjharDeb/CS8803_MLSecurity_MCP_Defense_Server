# middleware.py
from fastmcp.server.middleware import Middleware, MiddlewareContext

class DefenseMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercept every tool call going through the proxy.
        """
        result = await call_next(context)

        # Placeholder for hidden-payload detection (currently just adds "This has been verifed by a lone Yellow Jacket!" to the end of the content)
        content = getattr(result, "content", None)
        if content:
            for block in content:
                if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                    block.text = f"{block.text} This has been verifed by a lone Yellow Jacket!"

        data = getattr(result, "data", None)
        if isinstance(data, str):
            result.data = data + " This has been verifed by a lone Yellow Jacket!"

        return result