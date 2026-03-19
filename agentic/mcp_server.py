"""MCP Server — stdio transport for Claude Desktop / MCP host."""

from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_core.messages import HumanMessage

from src.agent.graph import agent_graph

load_dotenv()

mcp = FastMCP("ai-agent")


@mcp.tool()
async def invoke_agent(message: str) -> str:
    """Invoke the AI agent with a message."""
    state = {"messages": [HumanMessage(content=message)]}
    result = await agent_graph.ainvoke(state)
    return result["messages"][-1].content


if __name__ == "__main__":
    mcp.run()
