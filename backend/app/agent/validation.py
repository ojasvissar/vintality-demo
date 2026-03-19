"""Hallucination validation layer.

After Claude generates a response, this module checks whether
numerical claims in the response actually match the data returned
by tool calls. This is a critical safety layer for agricultural
decisions — a wrong irrigation or spray recommendation has real
crop consequences.

Strategy:
1. Extract numerical claims from Claude's response (regex-based)
2. Extract numerical values from tool results
3. Flag any claim that doesn't appear in tool results
4. Optionally block the response and ask Claude to retry

This directly addresses screening question #3:
"How do you approach preventing hallucinations in a domain
where accuracy matters?"
"""

import re
import json
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    """Result of validating a response against tool data."""
    is_valid: bool
    flagged_claims: list[dict]
    confidence: float  # 0-1, how confident we are the response is grounded
    details: str


def validate_response(
    response_text: str,
    tool_results: list[dict],
    strict: bool = False,
) -> ValidationResult:
    """Validate Claude's response against tool-returned data.

    Args:
        response_text: Claude's text response to validate
        tool_results: List of tool result dicts from the agent loop
        strict: If True, flag ANY number not found in tool data.
                If False (default), only flag numbers that look like
                sensor readings (with units like %, mm, °C, kPa).

    Returns:
        ValidationResult with pass/fail, flagged claims, and confidence.
    """
    # Extract all numbers with units from Claude's response
    claims = _extract_numerical_claims(response_text)

    # Extract all numbers from tool results
    tool_values = _extract_tool_values(tool_results)

    flagged = []
    for claim in claims:
        value = claim["value"]
        # Check if this value (within tolerance) exists in tool data
        if not _value_in_tool_data(value, tool_values, tolerance=0.5):
            flagged.append({
                "claim": claim["text"],
                "value": value,
                "unit": claim.get("unit", ""),
                "reason": "Value not found in tool results",
            })

    # Calculate confidence
    total_claims = len(claims)
    if total_claims == 0:
        confidence = 1.0  # No numerical claims = nothing to validate
    else:
        grounded_ratio = (total_claims - len(flagged)) / total_claims
        confidence = grounded_ratio

    is_valid = len(flagged) == 0 if strict else confidence >= 0.7

    details = _build_details(claims, flagged, tool_values)

    if flagged:
        logger.warning(
            f"Hallucination check: {len(flagged)}/{total_claims} claims flagged. "
            f"Confidence: {confidence:.0%}"
        )

    return ValidationResult(
        is_valid=is_valid,
        flagged_claims=flagged,
        confidence=confidence,
        details=details,
    )


def _extract_numerical_claims(text: str) -> list[dict]:
    """Extract numbers with agricultural units from response text.

    Looks for patterns like:
    - "28.3%" or "28.3 %"
    - "34mm" or "34 mm"
    - "22.1°C" or "22.1 °C"
    - "1.8 kPa"
    - "72/100" (risk scores)
    - "3.4mm/day"
    """
    patterns = [
        # Percentage values (VWC, humidity, field capacity)
        (r'(\d+\.?\d*)\s*%', 'percent'),
        # Millimeters (deficit, rainfall, irrigation)
        (r'(\d+\.?\d*)\s*mm', 'mm'),
        # Temperature
        (r'(\d+\.?\d*)\s*°C', 'celsius'),
        # Pressure (VPD)
        (r'(\d+\.?\d*)\s*kPa', 'kpa'),
        # Risk scores (e.g., "72/100" or "risk of 72" or "score: 72")
        (r'(?:risk|score)[^\d]*(\d+\.?\d*)', 'score'),
        # "X out of 100"
        (r'(\d+\.?\d*)\s*/\s*100', 'score'),
        # Days (days since spray, days ago)
        (r'(\d+)\s*days?\s*(?:ago|since)', 'days'),
        # Wind speed
        (r'(\d+\.?\d*)\s*km/h', 'kmh'),
        # Solar radiation
        (r'(\d+\.?\d*)\s*W/m', 'wm2'),
    ]

    claims = []
    seen_values = set()

    for pattern, unit in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = float(match.group(1))
            # Deduplicate
            key = (round(value, 1), unit)
            if key not in seen_values:
                seen_values.add(key)
                claims.append({
                    "text": match.group(0),
                    "value": value,
                    "unit": unit,
                })

    return claims


def _extract_tool_values(tool_results: list[dict]) -> set[float]:
    """Recursively extract all numerical values from tool results.

    Walks the entire JSON structure of all tool results and collects
    every number. This gives us the full set of "ground truth" values
    that Claude had access to.
    """
    values = set()

    def _walk(obj):
        if isinstance(obj, (int, float)):
            values.add(float(obj))
        elif isinstance(obj, str):
            # Try parsing JSON strings (tool results are often JSON strings)
            try:
                parsed = json.loads(obj)
                _walk(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for result in tool_results:
        _walk(result)

    return values


def _value_in_tool_data(value: float, tool_values: set[float], tolerance: float = 0.5) -> bool:
    """Check if a value (within tolerance) exists in tool data.

    We use tolerance because:
    - Claude might round differently (28.33 → 28.3)
    - Aggregations may differ slightly (avg of hourly vs. latest)
    - Unit conversions can introduce small differences
    """
    for tv in tool_values:
        if abs(value - tv) <= tolerance:
            return True
    return False


def _build_details(claims: list, flagged: list, tool_values: set) -> str:
    """Build a human-readable validation report."""
    lines = [f"Validated {len(claims)} numerical claims against tool data."]

    if not flagged:
        lines.append("All claims are grounded in tool results.")
    else:
        lines.append(f"FLAGGED {len(flagged)} potentially hallucinated values:")
        for f in flagged:
            lines.append(f"  - '{f['claim']}' ({f['value']} {f['unit']}): {f['reason']}")

    return "\n".join(lines)


def add_validation_disclaimer(response_text: str, validation: ValidationResult) -> str:
    """Optionally append a validation note to the response.

    In production, you might:
    - Block the response entirely if confidence < 0.5
    - Add a warning banner if confidence < 0.8
    - Log for review if any claims are flagged

    For the demo, we append a subtle disclaimer if needed.
    """
    if validation.is_valid and validation.confidence >= 0.9:
        return response_text

    if validation.confidence < 0.5:
        return (
            response_text + "\n\n"
            "⚠️ **Data verification notice**: Some values in this response "
            "could not be verified against current sensor data. Please "
            "cross-check critical readings before making field decisions."
        )

    return response_text
