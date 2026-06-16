import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from pathlib import Path
import io


REQUIRED_INTERVAL_COLS = [
    "scenario_id", "timestamp_local", "temperature_c", "relative_humidity_pct",
    "heat_index_c", "solar_irradiance_w_m2", "occupancy_count", "grid_available",
    "tariff_type", "tariff_pkr_per_kwh", "grid_carbon_kgco2_per_kwh", "non_cooling_load_kw"
]

REQUIRED_PROFILE_COLS = [
    "scenario_id", "name", "timezone", "building_type", "area_m2", "room_count",
    "max_occupancy", "insulation_level", "sun_exposure", "comfort_min_c",
    "comfort_max_c", "vulnerable_occupants", "budget_pkr_per_day", "maximum_grid_demand_kw"
]

REQUIRED_APPLIANCE_COLS = [
    "scenario_id", "appliance_id", "zone_id", "appliance_type", "quantity",
    "rated_power_kw", "cooling_capacity_kw", "efficiency_label",
    "min_runtime_minutes", "min_setpoint_c", "max_setpoint_c"
]


def load_excel(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    buf = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(buf)
    sheets = {}
    for sheet in xl.sheet_names:
        try:
            sheets[sheet.lower().strip()] = xl.parse(sheet)
        except Exception:
            pass
    return sheets


def _find_sheet(sheets: dict, candidates: List[str]) -> pd.DataFrame | None:
    for c in candidates:
        if c in sheets:
            return sheets[c]
    return None


def parse_workbook(sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    profiles_df = _find_sheet(sheets, ["scenario_profiles", "profiles", "scenarios"])
    appliances_df = _find_sheet(sheets, ["appliances", "appliance"])
    intervals_df = _find_sheet(sheets, ["interval_inputs", "intervals", "interval"])
    assets_df = _find_sheet(sheets, ["energy_assets", "assets", "solar_battery"])
    baseline_df = _find_sheet(sheets, ["baseline_schedule", "baseline"])

    return {
        "profiles": profiles_df,
        "appliances": appliances_df,
        "intervals": intervals_df,
        "assets": assets_df,
        "baseline": baseline_df,
    }


def validate_intervals(df: pd.DataFrame) -> Dict[str, Any]:
    errors = []
    warnings = []
    missing_fields = []

    for col in REQUIRED_INTERVAL_COLS:
        if col not in df.columns:
            missing_fields.append(col)

    if missing_fields:
        return {
            "is_valid": False,
            "total_records": len(df),
            "valid_records": 0,
            "errors": [{"field": f, "message": f"Required column '{f}' is missing"} for f in missing_fields],
            "warnings": [],
            "missing_fields": missing_fields,
        }

    df = df.copy()
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], errors="coerce")

    null_ts = df["timestamp_local"].isna().sum()
    if null_ts > 0:
        errors.append({"field": "timestamp_local", "message": f"{null_ts} unparseable timestamps"})

    # Check gaps per scenario to avoid false positives at scenario boundaries
    non_15 = 0
    if "scenario_id" in df.columns:
        for _, grp in df.sort_values("timestamp_local").groupby("scenario_id"):
            diffs = grp["timestamp_local"].diff().dropna()
            non_15 += (diffs != pd.Timedelta(minutes=15)).sum()
    else:
        df_sorted = df.sort_values("timestamp_local")
        diffs = df_sorted["timestamp_local"].diff().dropna()
        non_15 = (diffs != pd.Timedelta(minutes=15)).sum()
    if non_15 > 0:
        warnings.append({"field": "timestamp_local", "message": f"{non_15} gaps not exactly 15 minutes"})

    dups = df.duplicated(subset=["scenario_id", "timestamp_local"]).sum() if "scenario_id" in df.columns else df["timestamp_local"].duplicated().sum()
    if dups > 0:
        errors.append({"field": "timestamp_local", "message": f"{dups} duplicate timestamps"})

    bad_humidity = ((df["relative_humidity_pct"] < 0) | (df["relative_humidity_pct"] > 100)).sum()
    if bad_humidity > 0:
        errors.append({"field": "relative_humidity_pct", "message": f"{bad_humidity} values outside 0-100"})

    bad_temp = ((df["temperature_c"] < -20) | (df["temperature_c"] > 60)).sum()
    if bad_temp > 0:
        warnings.append({"field": "temperature_c", "message": f"{bad_temp} temperature outliers outside -20 to 60°C"})

    neg_irr = (df["solar_irradiance_w_m2"] < 0).sum()
    if neg_irr > 0:
        errors.append({"field": "solar_irradiance_w_m2", "message": f"{neg_irr} negative irradiance values"})

    neg_occ = (df["occupancy_count"] < 0).sum()
    if neg_occ > 0:
        errors.append({"field": "occupancy_count", "message": f"{neg_occ} negative occupancy counts"})

    neg_tariff = (df["tariff_pkr_per_kwh"] < 0).sum()
    if neg_tariff > 0:
        errors.append({"field": "tariff_pkr_per_kwh", "message": f"{neg_tariff} negative tariff values"})

    valid_records = len(df) - sum(1 for e in errors if "timestamp" in e["field"])

    return {
        "is_valid": len(errors) == 0,
        "total_records": len(df),
        "valid_records": max(0, valid_records),
        "errors": errors,
        "warnings": warnings,
        "missing_fields": missing_fields,
    }


def compute_heat_index(temp_c: float, rh: float) -> float:
    """Rothfusz regression for heat index."""
    T = temp_c * 9 / 5 + 32  # to Fahrenheit
    HI = (-42.379 + 2.04901523 * T + 10.14333127 * rh
          - 0.22475541 * T * rh - 0.00683783 * T ** 2
          - 0.05481717 * rh ** 2 + 0.00122874 * T ** 2 * rh
          + 0.00085282 * T * rh ** 2 - 0.00000199 * T ** 2 * rh ** 2)
    return (HI - 32) * 5 / 9  # back to Celsius


def fill_missing_heat_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mask = df["heat_index_c"].isna() | (df["heat_index_c"] == 0)
    df.loc[mask, "heat_index_c"] = df.loc[mask].apply(
        lambda r: compute_heat_index(r["temperature_c"], r["relative_humidity_pct"]), axis=1
    )
    return df
