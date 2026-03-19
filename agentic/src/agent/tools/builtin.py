from datetime import UTC, datetime

from langchain_core.tools import tool

from src.agent.tools.base import ToolRegistry

registry = ToolRegistry()


@tool
def get_current_time() -> str:
    """Returns the current UTC time."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


registry.register(get_current_time, tags=["utility", "time"])
