"""Tool function registry.

Provides execute_tool() which the orchestrator calls
when Claude requests a tool invocation.
"""

from app.tools.soil import get_soil_moisture
from app.tools.disease import get_disease_risk
from app.tools.weather import get_weather_forecast
from app.tools.canopy import get_canopy_environment
from app.tools.overview import get_farm_overview
from app.tools.knowledge_base import search_knowledge_base
from app.tools.definitions import TOOL_DEFINITIONS


# Registry maps tool names to callable functions
_REGISTRY = {
    "get_soil_moisture": get_soil_moisture,
    "get_disease_risk": get_disease_risk,
    "get_weather_forecast": get_weather_forecast,
    "get_canopy_environment": get_canopy_environment,
    "get_farm_overview": get_farm_overview,
    "search_knowledge_base": search_knowledge_base,
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name with the given input.

    This is the single dispatch point. The orchestrator calls
    this when Claude responds with a tool_use block.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of arguments from Claude

    Returns:
        JSON string result to send back to Claude

    Raises:
        ValueError: If tool_name is not registered
    """
    if tool_name not in _REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")

    func = _REGISTRY[tool_name]
    return func(**tool_input)
