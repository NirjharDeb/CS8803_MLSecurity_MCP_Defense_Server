"""Ronin Defense Proxy Server for MCP tool call protection."""

from fastmcp import FastMCP
from middleware import DefenseMiddleware

mcp = FastMCP.as_proxy(
    "https://ronin-mcp-v1.fastmcp.app/mcp",
    name="Ronin Defense Proxy Server",
)

mcp.add_middleware(DefenseMiddleware())

if __name__ == "__main__":
    mcp.run(transport="stdio")
