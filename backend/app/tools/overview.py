"""Tool: get_farm_overview

Provides a cross-block comparison of all blocks on the farm.
This is what a supervisor asks for first thing in the morning:
"What needs my attention today?"

Returns all blocks ranked by urgency — combining irrigation
deficit, disease risk, and sensor health into a priority list.
"""

import json
from app.database import execute_query


def get_farm_overview() -> str:
    """Get overview of all blocks with urgency ranking.

    Returns:
        JSON string with per-block status and priority ranking.
    """

    # Pull latest status for every block
    blocks_data = execute_query("""
        SELECT
            b.code AS block_code,
            b.varietal,
            b.area_ha,
            b.aspect,

            -- Latest soil moisture (avg across sensors in block)
            (SELECT ROUND(AVG(sr.vwc_percent)::numeric, 1)
             FROM sensor_readings_latest sr
             WHERE sr.block_code = b.code
               AND sr.sensor_type = 'soil_moisture') AS avg_vwc,

            -- Latest irrigation status
            ist.deficit_mm,
            ist.field_cap_pct,

            -- Latest disease risk
            dr.pm_risk_score,
            dr.botrytis_score,
            dr.days_since_spray,

            -- Last irrigation
            (SELECT started_at
             FROM irrigation_events ie
             WHERE ie.block_id = b.id
             ORDER BY started_at DESC LIMIT 1) AS last_irrigation

        FROM blocks b
        LEFT JOIN LATERAL (
            SELECT deficit_mm, field_cap_pct
            FROM irrigation_status
            WHERE block_id = b.id
            ORDER BY computed_at DESC LIMIT 1
        ) ist ON true
        LEFT JOIN LATERAL (
            SELECT pm_risk_score, botrytis_score, days_since_spray
            FROM disease_risk
            WHERE block_id = b.id
            ORDER BY computed_at DESC LIMIT 1
        ) dr ON true
        WHERE b.farm_id = 1
        ORDER BY b.code
    """)

    blocks = []
    for row in blocks_data:
        # Calculate urgency score (0-100)
        urgency = _calculate_urgency(row)

        blocks.append({
            "block": row["block_code"],
            "varietal": row["varietal"],
            "area_ha": float(row["area_ha"]) if row["area_ha"] else None,
            "soil_moisture": {
                "avg_vwc_pct": float(row["avg_vwc"]) if row["avg_vwc"] else None,
                "deficit_mm": round(float(row["deficit_mm"]), 1) if row["deficit_mm"] else None,
                "field_capacity_pct": round(float(row["field_cap_pct"]), 1) if row["field_cap_pct"] else None,
            },
            "disease": {
                "pm_risk_score": round(float(row["pm_risk_score"]), 1) if row["pm_risk_score"] else None,
                "botrytis_score": round(float(row["botrytis_score"]), 1) if row["botrytis_score"] else None,
                "days_since_spray": row["days_since_spray"],
            },
            "last_irrigation": row["last_irrigation"].isoformat() if row["last_irrigation"] else None,
            "urgency_score": urgency["score"],
            "urgency_reasons": urgency["reasons"],
        })

    # Sort by urgency (highest first)
    blocks.sort(key=lambda x: x["urgency_score"], reverse=True)

    return json.dumps({
        "farm": "Naramata Hills Vineyard",
        "blocks": blocks,
        "most_urgent": blocks[0]["block"] if blocks else None,
    }, default=str)


def _calculate_urgency(row: dict) -> dict:
    """Score block urgency 0-100 based on multiple factors."""
    score = 0
    reasons = []

    # Irrigation urgency
    vwc = float(row["avg_vwc"]) if row["avg_vwc"] else None
    deficit = float(row["deficit_mm"]) if row["deficit_mm"] else None
    fc = float(row["field_cap_pct"]) if row["field_cap_pct"] else None

    if vwc and vwc < 30:
        score += 35
        reasons.append(f"VWC critically low ({vwc}%)")
    elif vwc and vwc < 38:
        score += 15
        reasons.append(f"VWC below optimal ({vwc}%)")

    if deficit and deficit > 30:
        score += 20
        reasons.append(f"High irrigation deficit ({deficit}mm)")
    elif deficit and deficit > 15:
        score += 10

    if fc and fc < 45:
        score += 15
        reasons.append(f"Below field capacity threshold ({fc}%)")

    # Disease urgency
    pm = float(row["pm_risk_score"]) if row["pm_risk_score"] else None
    days_spray = row["days_since_spray"]

    if pm and pm > 65:
        score += 25
        reasons.append(f"PM risk high ({pm})")
    elif pm and pm > 45:
        score += 10

    if days_spray and days_spray > 10:
        score += 10
        reasons.append(f"Spray overdue ({days_spray} days)")

    return {"score": min(score, 100), "reasons": reasons}
