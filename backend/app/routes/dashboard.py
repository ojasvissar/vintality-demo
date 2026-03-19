"""Dashboard data API routes.

These endpoints power the visual dashboard panels alongside
the chat interface. They return the same data the tools query,
but formatted for chart rendering and status cards.
"""

from fastapi import APIRouter
from app.database import execute_query

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/blocks")
async def get_blocks_overview():
    """All blocks with latest status — powers the block status cards."""
    rows = execute_query("""
        SELECT
            b.code, b.name, b.varietal, b.area_ha, b.aspect, b.soil_type,
            (SELECT ROUND(AVG(sr.vwc_percent)::numeric, 1)
             FROM sensor_readings_latest sr
             WHERE sr.block_code = b.code AND sr.sensor_type = 'soil_moisture') AS avg_vwc,
            ist.deficit_mm, ist.field_cap_pct,
            dr.pm_risk_score, dr.botrytis_score, dr.days_since_spray,
            (SELECT started_at FROM irrigation_events ie
             WHERE ie.block_id = b.id ORDER BY started_at DESC LIMIT 1) AS last_irrigation
        FROM blocks b
        LEFT JOIN LATERAL (
            SELECT deficit_mm, field_cap_pct FROM irrigation_status
            WHERE block_id = b.id ORDER BY computed_at DESC LIMIT 1
        ) ist ON true
        LEFT JOIN LATERAL (
            SELECT pm_risk_score, botrytis_score, days_since_spray FROM disease_risk
            WHERE block_id = b.id ORDER BY computed_at DESC LIMIT 1
        ) dr ON true
        WHERE b.farm_id = 1 ORDER BY b.code
    """)
    return [_serialize(r) for r in rows]


@router.get("/blocks/{block_code}/soil-trend")
async def get_soil_trend(block_code: str):
    """7-day hourly VWC trend for a block — powers the soil moisture chart."""
    rows = execute_query("""
        SELECT
            date_trunc('hour', sr.recorded_at) AS hour,
            ROUND(AVG(sr.vwc_percent)::numeric, 1) AS vwc
        FROM sensor_readings sr
        JOIN sensors s ON s.id = sr.sensor_id
        JOIN blocks b ON b.id = s.block_id
        WHERE b.code = :code AND s.sensor_type = 'soil_moisture'
          AND sr.recorded_at > NOW() - INTERVAL '7 days'
        GROUP BY date_trunc('hour', sr.recorded_at)
        ORDER BY hour
    """, {"code": block_code})
    return [{"hour": str(r["hour"]), "vwc": float(r["vwc"])} for r in rows]


@router.get("/blocks/{block_code}/disease-trend")
async def get_disease_trend(block_code: str):
    """7-day daily PM risk trend for a block."""
    rows = execute_query("""
        SELECT
            DATE(computed_at) AS date,
            ROUND(AVG(pm_risk_score)::numeric, 1) AS pm_risk,
            ROUND(AVG(botrytis_score)::numeric, 1) AS botrytis,
            ROUND(AVG(driving_rh_pct)::numeric, 1) AS avg_rh
        FROM disease_risk
        WHERE block_id = (SELECT id FROM blocks WHERE code = :code AND farm_id = 1)
          AND computed_at > NOW() - INTERVAL '7 days'
        GROUP BY DATE(computed_at) ORDER BY date
    """, {"code": block_code})
    return [_serialize(r) for r in rows]


@router.get("/weather")
async def get_weather():
    """48h forecast — powers the weather strip."""
    rows = execute_query("""
        SELECT forecast_for, temp_c, humidity_pct, wind_speed_kmh,
               rain_prob_pct, frost_risk
        FROM weather_forecast
        WHERE farm_id = 1 AND forecast_for >= NOW()
        ORDER BY forecast_for LIMIT 48
    """)
    return [_serialize(r) for r in rows]


@router.get("/sensors")
async def get_sensor_status():
    """All sensors with connectivity status."""
    rows = execute_query("""
        SELECT s.code, s.sensor_type, s.position, s.status,
               s.last_seen, b.code AS block_code,
               EXTRACT(EPOCH FROM (NOW() - s.last_seen)) / 60 AS minutes_ago
        FROM sensors s
        JOIN blocks b ON b.id = s.block_id
        ORDER BY s.code
    """)
    return [_serialize(r) for r in rows]


def _serialize(row: dict) -> dict:
    """Convert Decimal/datetime to JSON-safe types."""
    out = {}
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            out[k] = v.isoformat()
        elif hasattr(v, 'as_integer_ratio'):
            out[k] = float(v)
        else:
            out[k] = v
    return out
