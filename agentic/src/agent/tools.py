from datetime import UTC, datetime

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """Returns the current UTC time."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


TOOLS = [get_current_time]
