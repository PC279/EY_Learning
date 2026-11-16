"""load MCP tools into a LangChain agent. Run: python -m part2.mcp_client"""
import asyncio
import sys

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from nimbus.model import get_model

client = MultiServerMCPClient({
    "nimbus-hr": {
        "transport": "stdio",                                  # start the server as a subprocess
        "command": sys.executable,
        "args": ["-m", "part7.mcp_server"],
    },
    # "it-desk": {"transport": "streamable_http", "url": "http://localhost:8000/mcp"},   # a remote server
})


async def main():
    tools = await client.get_tools()                           # MCP tools -> LangChain tools
    print([t.name for t in tools])
    agent = create_agent(get_model(), tools, system_prompt="You are Nimbus HR. Employee id: E101.")
    result = await agent.ainvoke({"messages": [{"role": "user", "content": "How many leave days do I have?"}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
