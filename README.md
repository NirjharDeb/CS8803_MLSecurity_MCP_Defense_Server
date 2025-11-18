# CS8803_MLSecurity_MCP_Defense_Server
An MCP defense server prototype for detecting and sanitizing hidden-payload delivery to LLMs in agentic IDEs (e.g., Cursor). Built exclusively for ML security research and defensive hardening - no malicious use.

## How is the MCP server hosted?
The MCP server is hosted on the cloud thanks to FastMCP Cloud. You can view the current deployment of the server at https://fastmcp.cloud/ronin-mcp/ronin-defense-mcp-v1/deployments. Whenever you commit and push a change to the `main` branch, it will automatically build and deploy onto the cloud.

## How to configure the MCP server for Cursor?
Go to File -> Preferences -> Cursor Settings -> Tools & MCP -> Installed MCP Servers. Create a new MCP server configuration using the following json:

```
{
  "mcpServers": {
    "ronin-defense-mcp-v1": {
      "url": "https://ronin-defense-mcp-v1.fastmcp.app/mcp",
      "headers": {}
    }
  }
}
```

Then, go back to Installed MCP Servers and refresh `ronin-defense-mcp-v1` until the light is green and it shows the tools associated with the Ronin MCP server.