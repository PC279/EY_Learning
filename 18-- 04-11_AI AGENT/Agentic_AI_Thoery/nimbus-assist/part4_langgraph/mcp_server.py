"""Expose Nimbus leave tools over the Model Context Protocol (MCP 2.x).
Run:  python -m part4_langgraph.mcp_server      (speaks MCP over stdio)
"""
from mcp.server.mcpserver import MCPServer

import nimbus_systems as ns

server = MCPServer("nimbus-hr")


@server.tool()
def get_leave_balance(employee_id: str) -> dict:
    """Get remaining annual leave days and probation limits for an employee."""
    return ns.get_leave_balance(employee_id)


@server.tool()
def apply_leave(employee_id: str, start_date: str, end_date: str, reason: str = "") -> dict:
    """Submit an annual leave request. Dates YYYY-MM-DD, inclusive. CHANGES DATA."""
    return ns.apply_leave(employee_id, start_date, end_date, reason)


if __name__ == "__main__":
    server.run()          # default transport: stdio; use server.run("streamable-http") for HTTP
