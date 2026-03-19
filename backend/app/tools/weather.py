"""Tool: get_weather_forecast

Retrieves the weather forecast for the farm.
This informs irrigation timing, spray windows, and frost risk.
"""

import json
from app.database import execute_query


def get_weather_forecast(hours_ahead: int = 24) -> str:
    """Get weather forecast for the farm.

    Args:
        hours_ahead: How many hours of forecast to return (max 48)

    Returns:
        JSON string with hourly forecast data.
    """
    hours_ahead = min(hours_ahead, 48)

    rows = execute_query("""
        SELECT
            forecast_for,
            temp_c,
            humidity_pct,
            wind_speed_kmh,
            rain_prob_pct,
            rain_mm,
            solar_rad_wm2,
            frost_risk
        FROM weather_forecast
        WHERE farm_id = 1
          AND forecast_for >= NOW()
          AND forecast_for <= NOW() + MAKE_INTERVAL(hours => :hours)
        ORDER BY forecast_for
    """, {"hours": hours_ahead})

    if not rows:
        return json.dumps({"error": "No forecast data available"})

    # Build summary stats
    temps = [float(r["temp_c"]) for r in rows if r["temp_c"]]
    rain_probs = [float(r["rain_prob_pct"]) for r in rows if r["rain_prob_pct"]]
    winds = [float(r["wind_speed_kmh"]) for r in rows if r["wind_speed_kmh"]]
    any_frost = any(r["frost_risk"] for r in rows)
    total_rain = sum(float(r["rain_mm"]) for r in rows if r["rain_mm"])

    result = {
        "forecast_hours": hours_ahead,
        "summary": {
            "temp_high_c": round(max(temps), 1) if temps else None,
            "temp_low_c": round(min(temps), 1) if temps else None,
            "max_rain_prob_pct": round(max(rain_probs), 1) if rain_probs else None,
            "total_rain_mm": round(total_rain, 1),
            "avg_wind_kmh": round(sum(winds) / len(winds), 1) if winds else None,
            "max_wind_kmh": round(max(winds), 1) if winds else None,
            "frost_risk": any_frost,
        },
        "spray_window": _assess_spray_window(rows),
        "hourly": [
            {
                "time": r["forecast_for"].isoformat(),
                "temp_c": round(float(r["temp_c"]), 1) if r["temp_c"] else None,
                "humidity_pct": round(float(r["humidity_pct"]), 1) if r["humidity_pct"] else None,
                "wind_kmh": round(float(r["wind_speed_kmh"]), 1) if r["wind_speed_kmh"] else None,
                "rain_prob_pct": round(float(r["rain_prob_pct"]), 1) if r["rain_prob_pct"] else None,
            }
            for r in rows[:12]  # Only return first 12 hours detail to save tokens
        ],
    }

    return json.dumps(result, default=str)


def _assess_spray_window(forecast_rows: list) -> dict:
    """Determine if there's a good spray window in the forecast.

    Good spray conditions: wind < 15 km/h, no rain within 6h,
    temp 15-30°C, humidity < 80%.
    """
    windows = []
    for r in forecast_rows:
        wind_ok = float(r["wind_speed_kmh"] or 0) < 15
        rain_ok = float(r["rain_prob_pct"] or 0) < 20
        temp = float(r["temp_c"] or 0)
        temp_ok = 15 <= temp <= 30
        hum_ok = float(r["humidity_pct"] or 0) < 80

        if all([wind_ok, rain_ok, temp_ok, hum_ok]):
            windows.append(r["forecast_for"].isoformat())

    return {
        "available": len(windows) > 0,
        "next_window_start": windows[0] if windows else None,
        "total_hours_available": len(windows),
    }
