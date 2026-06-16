import logging
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from ..utils.weather_api import fetch_weather_forecast, fetch_weather_historical, build_custom_scenario_intervals

logger = logging.getLogger("coolshift.weather")

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast")
async def get_forecast(
    lat: float = Query(24.8607, description="Latitude"),
    lon: float = Query(67.0011, description="Longitude"),
    days: int = Query(7, ge=1, le=16),
    timezone: str = Query("Asia/Karachi"),
):
    """Fetch live weather forecast from Open-Meteo (free, no key needed)."""
    logger.info(f"[FORECAST] Fetching {days}-day forecast for lat={lat}, lon={lon}")
    try:
        df = await fetch_weather_forecast(lat, lon, days, timezone)
        logger.info(f"[FORECAST] ✅ Got {len(df)} records from Open-Meteo")
        return JSONResponse({"records": len(df), "data": df.to_dict(orient="records")})
    except Exception as e:
        logger.error(f"[FORECAST] ❌ Weather API error: {e}")
        raise HTTPException(502, f"Weather API error: {e}")


@router.get("/custom-scenario")
async def generate_custom_scenario(
    scenario_id: str = Query("CUSTOM-1"),
    lat: float = Query(24.8607),
    lon: float = Query(67.0011),
    start_date: str = Query("2024-06-01"),
    end_date: str = Query("2024-06-07"),
    timezone: str = Query("Asia/Karachi"),
    has_outage: bool = Query(False),
):
    """
    Generate a complete custom 7-day scenario using live weather API.
    Fulfils the competition requirement for a team-created scenario.
    """
    logger.info(f"[CUSTOM] Generating scenario '{scenario_id}' — {start_date} to {end_date}, lat={lat}, lon={lon}, outage={has_outage}")
    used_synthetic = False
    try:
        df = await fetch_weather_historical(lat, lon, start_date, end_date, timezone)
        logger.info(f"[CUSTOM] ✅ Weather data fetched: {len(df)} records")
    except Exception as e:
        logger.warning(f"[CUSTOM] ⚠ Open-Meteo unavailable ({e}), using synthetic Karachi June data")
        used_synthetic = True
        df = _synthetic_karachi_june(start_date, end_date)

    outage_slots = [(2, 6)] if has_outage else None
    scenario_df = build_custom_scenario_intervals(df, scenario_id, outage_slots=outage_slots)
    logger.info(f"[CUSTOM] ✅ Custom scenario built: {len(scenario_df)} intervals, outage_slots={outage_slots}")

    source_label = "Synthetic (Karachi June typical profile)" if used_synthetic else "Open-Meteo ERA5 reanalysis (CC BY 4.0)"
    gen_method = "Synthetic diurnal model (15-min)" if used_synthetic else "API fetch + 15-min linear interpolation"

    # Convert timestamps to strings and sanitise NaN/Inf before JSON serialisation
    scenario_df = scenario_df.copy()
    scenario_df["timestamp_local"] = pd.to_datetime(scenario_df["timestamp_local"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    records = scenario_df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                rec[k] = None
            elif hasattr(v, "isoformat"):
                rec[k] = v.isoformat()

    return JSONResponse({
        "scenario_id": scenario_id,
        "source": "Open-Meteo Historical Weather API" if not used_synthetic else "Synthetic Karachi Profile",
        "source_url": "https://archive-api.open-meteo.com/v1/archive",
        "latitude": lat,
        "longitude": lon,
        "date_range": f"{start_date} to {end_date}",
        "records": len(scenario_df),
        "provenance": {
            "weather_source": source_label,
            "tariff_source": "Pakistan NEPRA domestic tariff 2024 (two-tier)",
            "occupancy": "Synthetic rule: occupied 08:00-22:00, 3 persons",
            "carbon_factor": "0.40-0.52 kgCO2e/kWh (NTDC grid average)",
            "generation_method": gen_method,
            "reproducible": True,
        },
        "data": records,
    })


def _synthetic_karachi_june(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Generate synthetic 15-min weather data for Karachi June.
    Based on climatological averages: day peak ~42°C, night min ~29°C.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    timestamps = []
    t = start
    while t < end:
        timestamps.append(t)
        t += timedelta(minutes=15)

    rows = []
    for ts in timestamps:
        hour_frac = ts.hour + ts.minute / 60.0
        # Diurnal curve: min at 05:00, max at 15:00
        temp = 29.0 + 13.0 * math.sin(math.pi * (hour_frac - 5.0) / 10.0) if 5 <= hour_frac <= 15 else max(
            29.0, 42.0 - 1.3 * abs(hour_frac - 15.0)
        )
        humidity = 60.0 - 10.0 * math.sin(math.pi * (hour_frac - 5.0) / 10.0) if 5 <= hour_frac <= 15 else 65.0
        heat_index = temp + 0.15 * max(0.0, humidity - 40.0)
        # Solar irradiance peaks at noon
        if 6 <= hour_frac <= 18:
            solar = 900.0 * math.sin(math.pi * (hour_frac - 6.0) / 12.0)
        else:
            solar = 0.0
        rows.append({
            "timestamp_local": ts,
            "temperature_c": round(temp, 2),
            "relative_humidity_pct": round(humidity, 1),
            "heat_index_c": round(heat_index, 2),
            "solar_irradiance_w_m2": round(solar, 1),
        })

    return pd.DataFrame(rows)
