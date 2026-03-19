"""Tool: get_soil_moisture

Retrieves current VWC (Volumetric Water Content) and recent trend
for a vineyard block. This is the most commonly called tool —
irrigation decisions depend on it.
"""

import json
from datetime import datetime
from app.database import execute_query


def get_soil_moisture(block_id: str, include_history: bool = False) -> str:
    """Get current soil moisture and irrigation status for a block.

    Args:
        block_id: Block code, e.g. 'B5'
        include_history: If True, include 7-day daily averages

    Returns:
        JSON string with soil moisture data for Claude to interpret.
    """

    # Current readings from all soil moisture sensors in the block
    current = execute_query("""
        SELECT
            s.code AS sensor_code,
            s.position,
            sr.vwc_percent,
            sr.soil_temp_c,
            sr.recorded_at
        FROM sensor_readings_latest sr
        JOIN sensors s ON s.id = sr.sensor_id
        WHERE sr.block_code = :block_id
          AND sr.sensor_type = 'soil_moisture'
    """, {"block_id": block_id})

    if not current:
        return json.dumps({"error": f"No soil moisture data for block {block_id}"})

    # Latest irrigation status (deficit, field capacity)
    irrigation = execute_query("""
        SELECT
            deficit_mm,
            field_cap_pct,
            etref_mm,
            etc_mm,
            pwp_proximity,
            computed_at
        FROM irrigation_status_latest
        WHERE block_code = :block_id
    """, {"block_id": block_id})

    # Last irrigation event
    last_irrigation = execute_query("""
        SELECT
            started_at,
            volume_mm,
            duration_min
        FROM irrigation_events
        WHERE block_id = (SELECT id FROM blocks WHERE code = :block_id AND farm_id = 1)
        ORDER BY started_at DESC
        LIMIT 1
    """, {"block_id": block_id})

    result = {
        "block": block_id,
        "sensors": [],
        "irrigation_status": None,
        "last_irrigation": None,
    }

    for row in current:
        result["sensors"].append({
            "sensor": row["sensor_code"],
            "position": row["position"],
            "vwc_percent": float(row["vwc_percent"]) if row["vwc_percent"] else None,
            "soil_temp_c": float(row["soil_temp_c"]) if row["soil_temp_c"] else None,
            "recorded_at": row["recorded_at"].isoformat() if row["recorded_at"] else None,
        })

    if irrigation:
        irr = irrigation[0]
        result["irrigation_status"] = {
            "deficit_mm": float(irr["deficit_mm"]) if irr["deficit_mm"] else None,
            "field_capacity_pct": float(irr["field_cap_pct"]) if irr["field_cap_pct"] else None,
            "etref_mm_daily": float(irr["etref_mm"]) if irr["etref_mm"] else None,
            "pwp_proximity_pct": float(irr["pwp_proximity"]) if irr["pwp_proximity"] else None,
            "computed_at": irr["computed_at"].isoformat() if irr["computed_at"] else None,
        }

    if last_irrigation:
        li = last_irrigation[0]
        days_ago = (datetime.now(li["started_at"].tzinfo) - li["started_at"]).days
        result["last_irrigation"] = {
            "date": li["started_at"].isoformat(),
            "days_ago": days_ago,
            "volume_mm": float(li["volume_mm"]) if li["volume_mm"] else None,
        }

    # Optional: 7-day trend (daily averages)
    if include_history:
        trend = execute_query("""
            SELECT
                DATE(sr.recorded_at) AS date,
                ROUND(AVG(sr.vwc_percent)::numeric, 1) AS avg_vwc
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            JOIN blocks b ON b.id = s.block_id
            WHERE b.code = :block_id
              AND s.sensor_type = 'soil_moisture'
              AND sr.recorded_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(sr.recorded_at)
            ORDER BY date
        """, {"block_id": block_id})

        result["trend_7d"] = [
            {"date": str(r["date"]), "avg_vwc": float(r["avg_vwc"])}
            for r in trend
        ]

    return json.dumps(result, default=str)
