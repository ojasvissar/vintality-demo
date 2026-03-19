"""Tool: get_disease_risk

Retrieves PM (Powdery Mildew) and Botrytis risk scores for a block,
including the driving conditions that are causing the risk level.
This is critical for spray timing decisions.
"""

import json
from app.database import execute_query


def get_disease_risk(block_id: str, include_history: bool = False) -> str:
    """Get current disease risk scores for a block.

    Args:
        block_id: Block code, e.g. 'B3'
        include_history: If True, include 7-day risk trajectory

    Returns:
        JSON string with disease risk data.
    """

    current = execute_query("""
        SELECT
            pm_risk_score,
            botrytis_score,
            driving_temp_c,
            driving_rh_pct,
            leaf_wetness_h,
            last_spray_date,
            days_since_spray,
            spray_efficacy_pct,
            computed_at,
            block_code,
            varietal
        FROM disease_risk_latest
        WHERE block_code = :block_id
    """, {"block_id": block_id})

    if not current:
        return json.dumps({"error": f"No disease risk data for block {block_id}"})

    row = current[0]
    result = {
        "block": block_id,
        "varietal": row["varietal"],
        "pm_risk": {
            "score": float(row["pm_risk_score"]),
            "level": _risk_level(float(row["pm_risk_score"])),
            "driving_temp_c": float(row["driving_temp_c"]),
            "driving_rh_pct": float(row["driving_rh_pct"]),
            "leaf_wetness_hours": float(row["leaf_wetness_h"]) if row["leaf_wetness_h"] else 0,
        },
        "botrytis_risk": {
            "score": float(row["botrytis_score"]),
            "level": _risk_level(float(row["botrytis_score"])),
        },
        "spray_status": {
            "last_spray_date": str(row["last_spray_date"]) if row["last_spray_date"] else None,
            "days_since_spray": row["days_since_spray"],
            "spray_efficacy_remaining_pct": float(row["spray_efficacy_pct"]) if row["spray_efficacy_pct"] else None,
        },
        "computed_at": row["computed_at"].isoformat() if row["computed_at"] else None,
    }

    if include_history:
        trend = execute_query("""
            SELECT
                DATE(computed_at) AS date,
                ROUND(AVG(pm_risk_score)::numeric, 1) AS avg_pm,
                ROUND(AVG(botrytis_score)::numeric, 1) AS avg_botrytis,
                ROUND(AVG(driving_rh_pct)::numeric, 1) AS avg_rh
            FROM disease_risk
            WHERE block_id = (SELECT id FROM blocks WHERE code = :block_id AND farm_id = 1)
              AND computed_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(computed_at)
            ORDER BY date
        """, {"block_id": block_id})

        result["trend_7d"] = [
            {
                "date": str(r["date"]),
                "avg_pm_risk": float(r["avg_pm"]),
                "avg_botrytis": float(r["avg_botrytis"]),
                "avg_rh": float(r["avg_rh"]),
            }
            for r in trend
        ]

    return json.dumps(result, default=str)


def _risk_level(score: float) -> str:
    """Convert numeric score to human-readable level."""
    if score >= 75:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "moderate"
    elif score >= 20:
        return "low"
    return "minimal"
