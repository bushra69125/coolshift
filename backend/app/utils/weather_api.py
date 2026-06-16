"""
Open-Meteo integration for custom scenario generation.
Free, no API key required, used by production companies worldwide.
"""

import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import math

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

KARACHI_LAT = 24.8607
KARACHI_LON = 67.0011


async def fetch_weather_forecast(
    lat: float = KARACHI_LAT,
    lon: float = KARACHI_LON,
    days: int = 7,
    timezone: str = "Asia/Karachi",
) -> pd.DataFrame:
    """Fetch 15-min resolution weather from Open-Meteo (7-day forecast)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "shortwave_radiation",
        ],
        "timezone": timezone,
        "forecast_days": min(days, 16),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    m15 = data.get("minutely_15", {})
    df = pd.DataFrame({
        "timestamp_local": pd.to_datetime(m15["time"]),
        "temperature_c": m15["temperature_2m"],
        "relative_humidity_pct": m15["relative_humidity_2m"],
        "heat_index_c": m15["apparent_temperature"],
        "solar_irradiance_w_m2": m15["shortwave_radiation"],
    })

    df = df.head(days * 96)
    return df


async def fetch_weather_historical(
    lat: float = KARACHI_LAT,
    lon: float = KARACHI_LON,
    start_date: str = "2024-06-01",
    end_date: str = "2024-06-07",
    timezone: str = "Asia/Karachi",
) -> pd.DataFrame:
    """Fetch historical weather for custom scenario."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "shortwave_radiation",
        ],
        "timezone": timezone,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(OPEN_METEO_HISTORICAL_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly", {})
    df_hourly = pd.DataFrame({
        "timestamp_local": pd.to_datetime(hourly["time"]),
        "temperature_c": hourly["temperature_2m"],
        "relative_humidity_pct": hourly["relative_humidity_2m"],
        "heat_index_c": hourly["apparent_temperature"],
        "solar_irradiance_w_m2": hourly["shortwave_radiation"],
    })

    # Upsample hourly → 15-minute via interpolation
    df_hourly = df_hourly.set_index("timestamp_local")
    df_15 = df_hourly.resample("15min").interpolate("time")
    df_15 = df_15.reset_index()
    df_15.columns = ["timestamp_local", "temperature_c", "relative_humidity_pct",
                     "heat_index_c", "solar_irradiance_w_m2"]
    df_15["solar_irradiance_w_m2"] = df_15["solar_irradiance_w_m2"].clip(lower=0)

    return df_15


def build_custom_scenario_intervals(
    weather_df: pd.DataFrame,
    scenario_id: str,
    tariff_schedule: Optional[dict] = None,
    occupancy_schedule: Optional[dict] = None,
    carbon_factor: float = 0.45,
    outage_slots: Optional[list] = None,
) -> pd.DataFrame:
    """Combine weather with tariff, occupancy, grid availability."""
    df = weather_df.copy()
    df["scenario_id"] = scenario_id

    # Default Pakistan two-tier tariff (PKR/kWh)
    if tariff_schedule is None:
        tariff_schedule = {
            "peak": {"hours": list(range(18, 23)), "rate": 32.5, "carbon": 0.52},
            "off_peak": {"hours": list(range(0, 18)) + [23], "rate": 18.0, "carbon": 0.40},
        }

    def get_tariff(ts):
        h = ts.hour
        for t_type, cfg in tariff_schedule.items():
            if h in cfg["hours"]:
                return t_type, cfg["rate"], cfg["carbon"]
        return "off_peak", 18.0, 0.40

    df[["tariff_type", "tariff_pkr_per_kwh", "grid_carbon_kgco2_per_kwh"]] = pd.DataFrame(
        df["timestamp_local"].apply(lambda ts: get_tariff(ts)).tolist(),
        index=df.index
    )

    # Default occupancy: 8am-10pm
    if occupancy_schedule is None:
        df["occupancy_count"] = df["timestamp_local"].apply(
            lambda ts: 3 if 8 <= ts.hour < 22 else 0
        )
    else:
        df["occupancy_count"] = df["timestamp_local"].apply(
            lambda ts: occupancy_schedule.get(ts.hour, 0)
        )

    # Grid availability: outage slots as list of (start_hour, end_hour) tuples
    df["grid_available"] = True
    if outage_slots:
        for (sh, eh) in outage_slots:
            mask = df["timestamp_local"].apply(lambda ts: sh <= ts.hour < eh)
            df.loc[mask, "grid_available"] = False

    df["non_cooling_load_kw"] = 0.3   # baseline appliance load

    return df[["scenario_id", "timestamp_local", "temperature_c", "relative_humidity_pct",
               "heat_index_c", "solar_irradiance_w_m2", "occupancy_count",
               "grid_available", "tariff_type", "tariff_pkr_per_kwh",
               "grid_carbon_kgco2_per_kwh", "non_cooling_load_kw"]]
