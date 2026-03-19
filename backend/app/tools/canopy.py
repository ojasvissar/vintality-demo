"""Tool: get_canopy_environment

Retrieves canopy temperature, humidity, and VPD for a block.
Also detects sensor divergence (one sensor reading differently
from others) — which could indicate a faulty sensor or
genuine microclimate variation.
"""

import json
from app.database import execute_query


def get_canopy_environment(block_id: str) -> str:
    """Get current canopy conditions for a block.

    Args:
        block_id: Block code, e.g. 'B3'

    Returns:
        JSON string with temperature, humidity, VPD, and
        sensor health assessment.
    """

    # Current readings from all T/H sensors in the block
    current = execute_query("""
        SELECT
            s.code AS sensor_code,
            s.position,
            sr.air_temp_c,
            sr.humidity_pct,
            sr.vpd_kpa,
            sr.recorded_at
        FROM sensor_readings_latest sr
        JOIN sensors s ON s.id = sr.sensor_id
        WHERE sr.block_code = :block_id
          AND sr.sensor_type = 'temp_humidity'
    """, {"block_id": block_id})

    if not current:
        return json.dumps({"error": f"No canopy data for block {block_id}"})

    sensors = []
    temps = []
    humidities = []
    vpds = []

    for row in current:
        temp = float(row["air_temp_c"]) if row["air_temp_c"] else None
        hum = float(row["humidity_pct"]) if row["humidity_pct"] else None
        vpd = float(row["vpd_kpa"]) if row["vpd_kpa"] else None

        sensors.append({
            "sensor": row["sensor_code"],
            "position": row["position"],
            "air_temp_c": round(temp, 1) if temp else None,
            "humidity_pct": round(hum, 1) if hum else None,
            "vpd_kpa": round(vpd, 3) if vpd else None,
            "recorded_at": row["recorded_at"].isoformat() if row["recorded_at"] else None,
        })

        if temp is not None:
            temps.append(temp)
        if hum is not None:
            humidities.append(hum)
        if vpd is not None:
            vpds.append(vpd)

    # Compute block averages and detect divergence
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None
    avg_hum = round(sum(humidities) / len(humidities), 1) if humidities else None
    avg_vpd = round(sum(vpds) / len(vpds), 3) if vpds else None

    # Divergence check: flag sensors > 2°C from average
    anomalies = []
    if avg_temp and len(temps) > 1:
        for s in sensors:
            if s["air_temp_c"] and abs(s["air_temp_c"] - avg_temp) > 2.0:
                anomalies.append({
                    "sensor": s["sensor"],
                    "reading": s["air_temp_c"],
                    "block_avg": avg_temp,
                    "deviation_c": round(s["air_temp_c"] - avg_temp, 1),
                    "note": "Reading >2°C from block average — possible sensor drift or microclimate"
                })

    result = {
        "block": block_id,
        "block_average": {
            "air_temp_c": avg_temp,
            "humidity_pct": avg_hum,
            "vpd_kpa": avg_vpd,
        },
        "sensors": sensors,
        "sensor_anomalies": anomalies if anomalies else None,
    }

    return json.dumps(result, default=str)
