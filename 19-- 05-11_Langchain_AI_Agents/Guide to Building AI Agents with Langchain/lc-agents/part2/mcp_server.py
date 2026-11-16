"""Part 2.7: an MCP server exposing Nimbus leave tools (MCP SDK 1.x, required by langchain-mcp-adapters).
Run by the client below; or alone: python -m part2.mcp_server
"""
from mcp.server.fastmcp import FastMCP

from nimbus import systems as ns

mcp = FastMCP("nimbus-hr")


@mcp.tool()
def get_leave_balance(employee_id: str) -> dict:
    """Get remaining annual leave days and probation limits for an employee."""
    return ns.get_leave_balance(employee_id)


@mcp.tool()
def search_hr_policies(query: str) -> dict:
    """Search Nimbus HR policies (leave, probation, travel, IT security)."""
    return ns.search_hr_policies(query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
