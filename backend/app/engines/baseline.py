"""
Baseline engine: computes how the user currently operates cooling.
Uses the baseline_schedule from the dataset (or a simple always-on rule).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .comfort import BuildingThermalState, estimate_indoor_temp, classify_comfort

DT_HOURS = 0.25  # 15 minutes


def compute_baseline(
    profile: Dict[str, Any],
    appliances: pd.DataFrame,
    intervals: pd.DataFrame,
    assets: Dict[str, Any],
    baseline_schedule: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per interval, containing all baseline metrics.
    """
    intervals = intervals.sort_values("timestamp_local").reset_index(drop=True)

    atype = appliances["appliance_type"].str.lower().str.strip() if len(appliances) > 0 else pd.Series([], dtype=str)
    ac_apps = appliances[atype.str.contains("ac", na=False)]
    fan_apps = appliances[atype.str.contains("fan|ceiling|pedestal", na=False)]

    total_ac_units = int(ac_apps["quantity"].sum()) if len(ac_apps) > 0 else 0
    total_fan_units = int(fan_apps["quantity"].sum()) if len(fan_apps) > 0 else 0
    ac_rated_kw = float(ac_apps["rated_power_kw"].sum()) if len(ac_apps) > 0 else 0.0
    ac_cooling_kw = float(ac_apps["cooling_capacity_kw"].sum()) if len(ac_apps) > 0 else 0.0
    fan_rated_kw = float(fan_apps["rated_power_kw"].sum()) if len(fan_apps) > 0 else 0.0
    default_setpoint = float(ac_apps["max_setpoint_c"].min()) if len(ac_apps) > 0 else 24.0

    state = BuildingThermalState(
        indoor_temp_c=float(intervals["temperature_c"].iloc[0]) - 2.0,
        area_m2=float(profile["area_m2"]),
        insulation_level=str(profile["insulation_level"]),
        sun_exposure=str(profile["sun_exposure"]),
        comfort_min_c=float(profile["comfort_min_c"]),
        comfort_max_c=float(profile["comfort_max_c"]),
        vulnerable_occupants=bool(profile.get("vulnerable_occupants", False)),
    )

    rows = []
    soc = float(assets.get("initial_soc_kwh", 0.0))
    battery_cap = float(assets.get("battery_capacity_kwh", 0.0))
    solar_cap = float(assets.get("solar_capacity_kw", 0.0))
    solar_eff = float(assets.get("solar_conversion_efficiency", 0.18))

    # Pre-build baseline lookup keyed on normalized timestamp string
    bs_lookup = {}
    if baseline_schedule is not None and len(baseline_schedule) > 0:
        bs = baseline_schedule.copy()
        bs["_ts"] = pd.to_datetime(bs["timestamp_local"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        if "scenario_id" in bs.columns:
            sid = str(intervals["scenario_id"].iloc[0])
            bs = bs[bs["scenario_id"].astype(str) == sid]
        for _, brow in bs.iterrows():
            bs_lookup[brow["_ts"]] = brow

    for i, row in intervals.iterrows():
        occ = int(row["occupancy_count"])
        grid_ok = bool(row["grid_available"])
        ts_key = pd.to_datetime(row["timestamp_local"]).strftime("%Y-%m-%d %H:%M:%S")

        if bs_lookup:
            brow = bs_lookup.get(ts_key)
            if brow is not None:
                ac_on = int(brow["baseline_ac_units_on"])
                raw_sp = brow["baseline_ac_setpoint_c"]
                ac_sp = float(raw_sp) if pd.notna(raw_sp) else default_setpoint
                fan_on = int(brow["baseline_fan_units_on"])
            else:
                ac_on, ac_sp, fan_on = _default_baseline_decision(
                    occ, total_ac_units, total_fan_units, default_setpoint,
                    row["temperature_c"], grid_ok
                )
        else:
            ac_on, ac_sp, fan_on = _default_baseline_decision(
                occ, total_ac_units, total_fan_units, default_setpoint,
                row["temperature_c"], grid_ok
            )

        # If no grid, can't run AC on grid (simplified: assume no battery in baseline)
        if not grid_ok:
            ac_on = 0
            fan_on = 0

        # Energy
        ac_energy = (ac_rated_kw * ac_on / max(total_ac_units, 1)) * DT_HOURS if total_ac_units > 0 else 0.0
        fan_energy = (fan_rated_kw * fan_on / max(total_fan_units, 1)) * DT_HOURS if total_fan_units > 0 else 0.0
        non_cool = float(row.get("non_cooling_load_kw", 0.0)) * DT_HOURS
        cooling_energy = ac_energy + fan_energy

        # Solar production
        irr = float(row.get("solar_irradiance_w_m2", 0.0))
        solar_gen = solar_cap * (irr / 1000) * solar_eff * DT_HOURS if solar_cap > 0 else 0.0
        solar_used = min(solar_gen, cooling_energy + non_cool)

        # Battery (not modelled in baseline for simplicity)
        bat_ch = max(0, min(solar_gen - solar_used,
                            float(assets.get("max_charge_kw", 0)) * DT_HOURS,
                            battery_cap - soc))
        soc = min(battery_cap, soc + bat_ch * float(assets.get("charge_efficiency", 0.95)))

        grid_energy = max(0.0, cooling_energy + non_cool - solar_used)
        if not grid_ok:
            grid_energy = 0.0

        cost = grid_energy * float(row["tariff_pkr_per_kwh"])
        emissions = grid_energy * float(row["grid_carbon_kgco2_per_kwh"])

        # Thermal model
        active_cooling_kw = (ac_cooling_kw * ac_on / max(total_ac_units, 1)) if total_ac_units > 0 else 0.0
        indoor_temp = estimate_indoor_temp(
            state, row["temperature_c"], row["heat_index_c"],
            occ, active_cooling_kw, ac_sp if ac_on > 0 else None,
            irr,
        )
        state.indoor_temp_c = indoor_temp
        comfort = classify_comfort(
            indoor_temp, state.comfort_min_c, state.comfort_max_c,
            occ > 0, state.vulnerable_occupants
        )

        rows.append({
            "scenario_id": row["scenario_id"],
            "timestamp_local": row["timestamp_local"],
            "baseline_ac_units_on": ac_on,
            "baseline_ac_setpoint_c": ac_sp,
            "baseline_fan_units_on": fan_on,
            "baseline_grid_energy_kwh": grid_energy,
            "baseline_solar_used_kwh": solar_used,
            "baseline_battery_soc_kwh": soc,
            "baseline_cooling_energy_kwh": cooling_energy,
            "baseline_indoor_temp_c": indoor_temp,
            "baseline_comfort_status": comfort,
            "baseline_cost_pkr": cost,
            "baseline_emissions_kgco2e": emissions,
            "occupancy_count": occ,
            "grid_available": grid_ok,
            "tariff_pkr_per_kwh": float(row["tariff_pkr_per_kwh"]),
            "temperature_c": float(row["temperature_c"]),
            "heat_index_c": float(row["heat_index_c"]),
            "solar_irradiance_w_m2": irr,
        })

    return pd.DataFrame(rows)


def _default_baseline_decision(occ, total_ac, total_fan, default_sp, temp_c, grid_ok):
    """Always-on rule: run all AC when occupied, all fans when very hot."""
    if not grid_ok:
        return 0, default_sp, 0
    if occ > 0:
        return total_ac, default_sp, total_fan
    elif temp_c > 35:
        return max(1, total_ac // 2), default_sp, total_fan
    else:
        return 0, default_sp, 0


def summarize_baseline(df: pd.DataFrame) -> Dict[str, float]:
    return {
        "total_energy_kwh": round(df["baseline_grid_energy_kwh"].sum(), 3),
        "total_cost_pkr": round(df["baseline_cost_pkr"].sum(), 2),
        "peak_demand_kw": round(df["baseline_grid_energy_kwh"].max() / DT_HOURS, 3),
        "total_emissions_kgco2e": round(df["baseline_emissions_kgco2e"].sum(), 3),
        "total_cooling_kwh": round(df["baseline_cooling_energy_kwh"].sum(), 3),
        "comfort_compliance_pct": round(
            (df["baseline_comfort_status"] == "within_range").sum() / max(1, (df["occupancy_count"] > 0).sum()) * 100, 1
        ),
        "unsafe_intervals": int((df["baseline_comfort_status"].isin(["unsafe", "infeasible"])).sum()),
    }
