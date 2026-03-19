"""Tool definitions for Claude's function calling interface.

Each tool has:
  - name: identifier Claude uses to call it
  - description: helps Claude decide WHEN to use this tool
  - input_schema: JSON Schema for the function parameters

The descriptions are critical — they're prompt engineering at
the tool level. Better descriptions = better tool selection.
"""

TOOL_DEFINITIONS = [
    {
        "name": "get_soil_moisture",
        "description": (
            "Get current soil moisture (VWC), irrigation deficit, field capacity, "
            "and last irrigation date for a specific vineyard block. Use this when "
            "the user asks about soil conditions, water status, irrigation needs, "
            "or whether a block is dry. Returns data from soil moisture sensors "
            "and the irrigation model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "Block code, e.g. 'B5', 'B3'. Must match a block in the farm configuration.",
                },
                "include_history": {
                    "type": "boolean",
                    "description": "If true, include 7-day daily VWC averages to show the drying/wetting trend.",
                    "default": False,
                },
            },
            "required": ["block_id"],
        },
    },
    {
        "name": "get_disease_risk",
        "description": (
            "Get current Powdery Mildew (PM) and Botrytis risk scores for a "
            "vineyard block, including the driving conditions (temperature, humidity, "
            "leaf wetness) and spray program status. Use this when the user asks "
            "about disease risk, spray timing, PM, Botrytis, or canopy health. "
            "PM risk above 60 is considered high and warrants spray action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "Block code, e.g. 'B3'",
                },
                "include_history": {
                    "type": "boolean",
                    "description": "If true, include 7-day risk score trajectory.",
                    "default": False,
                },
            },
            "required": ["block_id"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": (
            "Get weather forecast for the farm for the next 24-48 hours. Includes "
            "temperature, humidity, wind, rain probability, frost risk, and spray "
            "window assessment. Use this when the user asks about weather, whether "
            "it's safe to spray or irrigate, frost risk, or upcoming conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours_ahead": {
                    "type": "integer",
                    "description": "Number of hours of forecast to retrieve (max 48).",
                    "default": 24,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_canopy_environment",
        "description": (
            "Get current canopy temperature, humidity, and VPD (Vapour Pressure "
            "Deficit) for a specific block, with readings from all T/H sensors. "
            "Also detects sensor divergence — when one sensor reads significantly "
            "differently from others, which may indicate a faulty sensor or "
            "microclimate. Use this for temperature, humidity, VPD queries, or "
            "when investigating sensor anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "Block code, e.g. 'B9'",
                },
            },
            "required": ["block_id"],
        },
    },
    {
        "name": "get_farm_overview",
        "description": (
            "Get a cross-block comparison of all blocks on the farm, ranked by "
            "urgency. Shows soil moisture, disease risk, and irrigation status "
            "for every block. Use this when the user asks 'what needs attention', "
            "'which blocks are at risk', 'give me the morning summary', or any "
            "question comparing multiple blocks. This is the first tool to call "
            "when the user asks a broad question about the whole farm."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the sensor documentation and troubleshooting knowledge base. "
            "Use this when the user asks about sensor installation, calibration "
            "procedures, LoRaWAN/TTN connectivity issues, sensor placement "
            "recommendations, or any hardware/infrastructure question that is NOT "
            "about current sensor readings. This searches documentation, manuals, "
            "and SOPs — not live sensor data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about sensor docs",
                },
                "category": {
                    "type": "string",
                    "enum": ["calibration", "troubleshooting", "installation", "connectivity"],
                    "description": "Optional category filter to narrow results",
                },
            },
            "required": ["query"],
        },
    },
]

# Map tool names to their Python functions
# This is used by the orchestrator to dispatch tool calls
TOOL_FUNCTIONS = {
    "get_soil_moisture": "app.tools.soil:get_soil_moisture",
    "get_disease_risk": "app.tools.disease:get_disease_risk",
    "get_weather_forecast": "app.tools.weather:get_weather_forecast",
    "get_canopy_environment": "app.tools.canopy:get_canopy_environment",
    "get_farm_overview": "app.tools.overview:get_farm_overview",
    "search_knowledge_base": "app.tools.knowledge_base:search_knowledge_base",
}
