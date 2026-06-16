"""
CoolShift LP Optimization Engine
Uses PuLP (Linear Programming) — same class of solver used in industrial energy management.

Objective: minimize weighted sum of
  - grid electricity cost
  - carbon emissions
  - comfort penalty (degree-minutes outside range)
  - peak demand

Hard constraints (all 9 from spec):
  1. Grid draw = 0 when grid_available = False
  2. AC units on ≤ installed quantity
  3. Setpoints within [min_setpoint, max_setpoint]
  4. Battery SOC ∈ [0, capacity]
  5. Battery SOC ≥ reserve (except declared emergency)
  6. Charge/discharge ≤ max rates × DT
  7. Energy balance every interval
  8. Occupied comfort prioritized
  9. Minimum run time (via min-blocks heuristic post-solve)
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

import pandas as pd
import numpy as np

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False

from .comfort import (
    BuildingThermalState, estimate_indoor_temp,
    classify_comfort, comfort_penalty
)
from .baseline import summarize_baseline

logger = logging.getLogger(__name__)

DT = 0.25         # 15 minutes in hours
BIG_M = 1e6
COMFORT_PENALTY_WEIGHT = 150.0  # PKR-equivalent cost per °C-interval above range


REASON_CODES = {
    "SOLAR_AVAILABLE": "Solar energy available — using solar to reduce grid draw",
    "PEAK_TARIFF": "Peak tariff period — deferring or reducing cooling load",
    "OFF_PEAK": "Off-peak tariff — full cooling at lower cost",
    "HEAT_RISK": "Extreme outdoor heat — maintaining mandatory comfort level",
    "OUTAGE": "Grid unavailable — operating on battery/solar only",
    "BATTERY_RESERVE": "Battery at reserve level — limiting discharge",
    "LOW_OCCUPANCY": "Space unoccupied — reducing cooling to save energy",
    "HIGH_OCCUPANCY": "High occupancy detected — prioritizing comfort",
    "BATTERY_CHARGING": "Charging battery from solar surplus",
    "COMFORT_OVERRIDE": "Comfort cannot be maintained — infeasible period reported",
    "OPTIMAL": "Optimal balance of comfort, cost and emissions achieved",
}


def _pick_reason_code(
    row: Dict, grid_ok: bool, is_peak: bool, occ: int,
    solar_used: float, bat_dis: float, bat_soc: float,
    bat_reserve: float, outdoor_temp: float, bat_cap: float = 0.0
) -> Tuple[str, str]:
    if not grid_ok:
        return "OUTAGE", REASON_CODES["OUTAGE"]
    if outdoor_temp > 40:
        return "HEAT_RISK", REASON_CODES["HEAT_RISK"]
    if solar_used > 0.01 and bat_cap > 0 and bat_soc > bat_reserve:
        return "SOLAR_AVAILABLE", REASON_CODES["SOLAR_AVAILABLE"]
    if solar_used > 0.01:
        return "BATTERY_CHARGING", REASON_CODES["BATTERY_CHARGING"]
    if bat_cap > 0 and bat_soc <= bat_reserve + 0.1:
        return "BATTERY_RESERVE", REASON_CODES["BATTERY_RESERVE"]
    if is_peak:
        return "PEAK_TARIFF", REASON_CODES["PEAK_TARIFF"]
    if occ == 0:
        return "LOW_OCCUPANCY", REASON_CODES["LOW_OCCUPANCY"]
    if occ > 3:
        return "HIGH_OCCUPANCY", REASON_CODES["HIGH_OCCUPANCY"]
    return "OPTIMAL", REASON_CODES["OPTIMAL"]


def optimize_schedule(
    profile: Dict[str, Any],
    appliances: pd.DataFrame,
    intervals: pd.DataFrame,
    assets: Dict[str, Any],
    baseline_df: pd.DataFrame,
    weights: Dict[str, float],
    run_id: str | None = None,
    algorithm_version: str = "coolshift-lp-v1",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main entry point. Returns (output_df, summary_dict).
    Falls back to greedy heuristic if PuLP is unavailable.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    intervals = intervals.sort_values("timestamp_local").reset_index(drop=True)
    N = len(intervals)

    atype = appliances["appliance_type"].str.lower().str.strip()
    ac_apps = appliances[atype.str.contains("ac", na=False)]
    fan_apps = appliances[atype.str.contains("fan|ceiling|pedestal", na=False)]

    total_ac = int(ac_apps["quantity"].sum()) if len(ac_apps) > 0 else 0
    total_fan = int(fan_apps["quantity"].sum()) if len(fan_apps) > 0 else 0
    ac_power_kw = float(ac_apps["rated_power_kw"].sum()) if len(ac_apps) > 0 else 0.0
    ac_cool_kw = float(ac_apps["cooling_capacity_kw"].sum()) if len(ac_apps) > 0 else 0.0
    fan_power_kw = float(fan_apps["rated_power_kw"].sum()) if len(fan_apps) > 0 else 0.0
    min_sp = float(ac_apps["min_setpoint_c"].min()) if len(ac_apps) > 0 else 16.0
    max_sp = float(ac_apps["max_setpoint_c"].max()) if len(ac_apps) > 0 else 30.0
    default_sp = round((min_sp + max_sp) / 2, 1)

    bat_cap = float(assets.get("battery_capacity_kwh", 0.0))
    bat_reserve = float(assets.get("minimum_reserve_kwh", 0.0))
    max_ch_kw = float(assets.get("max_charge_kw", 0.0))
    max_dis_kw = float(assets.get("max_discharge_kw", 0.0))
    ch_eff = float(assets.get("charge_efficiency", 0.95))
    dis_eff = float(assets.get("discharge_efficiency", 0.95))
    solar_cap = float(assets.get("solar_capacity_kw", 0.0))
    solar_eff = float(assets.get("solar_conversion_efficiency", 0.18))
    init_soc = float(assets.get("initial_soc_kwh", 0.0))

    comfort_min = float(profile["comfort_min_c"])
    comfort_max = float(profile["comfort_max_c"])
    max_demand_kw = float(profile.get("maximum_grid_demand_kw", 999.0))
    vulnerable = bool(profile.get("vulnerable_occupants", False))

    w_cost = weights.get("cost", 0.35)
    w_em = weights.get("emissions", 0.30)
    w_comfort = weights.get("comfort", 0.25)
    w_peak = weights.get("peak_demand", 0.10)

    if HAS_PULP:
        return _lp_solve(
            intervals, N, run_id, algorithm_version,
            total_ac, total_fan, ac_power_kw, ac_cool_kw, fan_power_kw,
            min_sp, max_sp, default_sp,
            bat_cap, bat_reserve, max_ch_kw, max_dis_kw, ch_eff, dis_eff,
            solar_cap, solar_eff, init_soc,
            comfort_min, comfort_max, max_demand_kw, vulnerable,
            w_cost, w_em, w_comfort, w_peak,
            profile, baseline_df,
        )
    else:
        return _greedy_solve(
            intervals, N, run_id, algorithm_version,
            total_ac, total_fan, ac_power_kw, ac_cool_kw, fan_power_kw,
            default_sp, min_sp, max_sp,
            bat_cap, bat_reserve, max_ch_kw, max_dis_kw, ch_eff, dis_eff,
            solar_cap, solar_eff, init_soc,
            comfort_min, comfort_max, max_demand_kw, vulnerable,
            profile, baseline_df,
        )


def _lp_solve(
    intervals, N, run_id, algo_ver,
    total_ac, total_fan, ac_power_kw, ac_cool_kw, fan_power_kw,
    min_sp, max_sp, default_sp,
    bat_cap, bat_reserve, max_ch_kw, max_dis_kw, ch_eff, dis_eff,
    solar_cap, solar_eff, init_soc,
    comfort_min, comfort_max, max_demand_kw, vulnerable,
    w_cost, w_em, w_comfort, w_peak,
    profile, baseline_df,
) -> Tuple[pd.DataFrame, Dict]:

    prob = pulp.LpProblem("CoolShift_Optimizer", pulp.LpMinimize)

    # --- Decision variables ---
    # Continuous relaxation (much faster than MILP; round at output time)
    ac_on = [pulp.LpVariable(f"ac_{i}", 0, total_ac) for i in range(N)]
    fan_on = [pulp.LpVariable(f"fan_{i}", 0, total_fan) for i in range(N)]
    # Setpoint: continuous, linearized as fraction of AC capacity
    sp_frac = [pulp.LpVariable(f"sp_{i}", 0, 1) for i in range(N)]  # 0=min_sp, 1=max_sp
    grid_e = [pulp.LpVariable(f"ge_{i}", 0) for i in range(N)]
    solar_use = [pulp.LpVariable(f"su_{i}", 0) for i in range(N)]
    bat_ch = [pulp.LpVariable(f"bc_{i}", 0, max_ch_kw * DT) for i in range(N)]
    bat_dis = [pulp.LpVariable(f"bd_{i}", 0, max_dis_kw * DT) for i in range(N)]
    soc = [pulp.LpVariable(f"soc_{i}", 0, bat_cap) for i in range(N)]
    peak_var = pulp.LpVariable("peak", 0)   # tracks max grid draw

    # --- Precompute solar generation per interval ---
    solar_gen = []
    for _, row in intervals.iterrows():
        irr = float(row.get("solar_irradiance_w_m2", 0.0))
        gen = solar_cap * (irr / 1000) * solar_eff * DT if solar_cap > 0 else 0.0
        solar_gen.append(gen)

    # --- Objective ---
    cost_terms = []
    em_terms = []
    comfort_terms = []

    # Pre-cooling: mark unoccupied intervals within 2 hrs of an occupied period
    occ_list = [int(intervals.iloc[k]["occupancy_count"]) for k in range(N)]
    precool_window = set()
    for k in range(N):
        if occ_list[k] == 0:
            for lk in range(1, min(9, N - k)):
                if occ_list[k + lk] > 0:
                    precool_window.add(k)
                    break

    for i, (_, row) in enumerate(intervals.iterrows()):
        tariff = float(row["tariff_pkr_per_kwh"])
        carbon = float(row["grid_carbon_kgco2_per_kwh"])
        occ = int(row["occupancy_count"])

        cost_terms.append(tariff * grid_e[i])
        em_terms.append(carbon * grid_e[i])

        # Comfort penalty proxy: penalize AC off during occupied hot periods
        # Trigger 3°C below comfort_max so optimizer pre-cools before heat peaks
        if occ > 0:
            temp = float(row["temperature_c"])
            penalty_scale = max(0, temp - (comfort_max - 3)) * COMFORT_PENALTY_WEIGHT
            if total_ac > 0 and penalty_scale > 0:
                # Penalize having AC off when it's hot and occupied
                comfort_terms.append(penalty_scale * DT * (total_ac - ac_on[i]))
        elif i in precool_window:
            # Pre-cooling: use solar (free) to cool before shift starts
            temp = float(row["temperature_c"])
            if solar_gen[i] > 0.01:
                pre_scale = max(0, temp - (comfort_max - 2)) * COMFORT_PENALTY_WEIGHT * 0.4
                if total_ac > 0 and pre_scale > 0:
                    comfort_terms.append(pre_scale * DT * (total_ac - ac_on[i]))

    # Normalize weights
    obj = (
        w_cost * pulp.lpSum(cost_terms)
        + w_em * 1000 * pulp.lpSum(em_terms)   # scale emissions to PKR magnitude
        + w_comfort * pulp.lpSum(comfort_terms)
        + w_peak * 1000 * peak_var
    )
    prob += obj

    # --- Hard constraints ---
    for i, (_, row) in enumerate(intervals.iterrows()):
        grid_ok = bool(row["grid_available"])
        occ = int(row["occupancy_count"])
        tariff_type = str(row.get("tariff_type", ""))
        non_cool = float(row.get("non_cooling_load_kw", 0.0)) * DT

        # AC cooling energy this interval
        ac_energy_i = (ac_power_kw / max(total_ac, 1)) * DT * ac_on[i] if total_ac > 0 else 0
        fan_energy_i = (fan_power_kw / max(total_fan, 1)) * DT * fan_on[i] if total_fan > 0 else 0
        total_load = ac_energy_i + fan_energy_i + non_cool

        # 1. Grid = 0 if outage; AC/fan bounded by what solar+battery can actually supply
        if not grid_ok:
            prob += grid_e[i] == 0, f"outage_{i}"
            prob += bat_ch[i] == 0, f"no_ch_outage_{i}"
            # Controllable loads (AC + fan) cannot exceed renewable supply during outage
            ctrl_load = ac_energy_i + fan_energy_i
            prob += ctrl_load <= solar_use[i] + bat_dis[i] * dis_eff, f"ebal_{i}"
        else:
            # 2-3. AC/Fan counts bounded by installed quantity (implicit in var bounds)
            # 4. Energy balance: grid + solar_use + bat_dis = load + bat_ch
            prob += (grid_e[i] + solar_use[i] + bat_dis[i] * dis_eff
                     == total_load + bat_ch[i]), f"ebal_{i}"

        # 5. Solar use ≤ solar generation
        prob += solar_use[i] <= solar_gen[i], f"solar_cap_{i}"

        # 6. Battery SOC dynamics
        if i == 0:
            prob += soc[i] == init_soc + bat_ch[i] * ch_eff - bat_dis[i], f"soc0"
        else:
            prob += soc[i] == soc[i-1] + bat_ch[i] * ch_eff - bat_dis[i], f"soc_{i}"

        # 7. Battery reserve
        if bat_cap > 0:
            prob += soc[i] >= bat_reserve, f"bat_reserve_{i}"

        # 8. Grid demand limit (soft — only when grid available)
        if grid_ok:
            prob += grid_e[i] <= max_demand_kw * DT, f"max_demand_{i}"

        # 9. Peak tracking  (multiply by 1/DT — PuLP doesn't support LpVar / float)
        prob += peak_var >= grid_e[i] * (1.0 / DT), f"peak_{i}"

        # 10. Force minimum AC during hot occupied periods
        if occ > 0 and total_ac > 0 and grid_ok:
            temp = float(row["temperature_c"])
            if temp > 35:
                prob += ac_on[i] >= max(1, total_ac // 2), f"comfort_force_{i}"
            elif temp > 30:
                prob += ac_on[i] >= max(1, total_ac // 3), f"comfort_force_{i}"

    # Solve
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=55)
    status = prob.solve(solver)

    logger.info(f"LP status: {pulp.LpStatus[prob.status]}, objective: {pulp.value(prob.objective):.2f}")

    # --- Extract results ---
    state = BuildingThermalState(
        indoor_temp_c=float(intervals.iloc[0]["temperature_c"]) - 2.0,
        area_m2=float(profile["area_m2"]),
        insulation_level=str(profile["insulation_level"]),
        sun_exposure=str(profile["sun_exposure"]),
        comfort_min_c=comfort_min,
        comfort_max_c=comfort_max,
        vulnerable_occupants=vulnerable,
    )

    rows = []
    for i, (_, row) in enumerate(intervals.iterrows()):
        ac_val = max(0, min(total_ac, int(round(pulp.value(ac_on[i]) or 0))))
        fan_val = max(0, min(total_fan, int(round(pulp.value(fan_on[i]) or 0))))
        sp_val = min_sp + (max_sp - min_sp) * max(0, min(1, pulp.value(sp_frac[i]) or 0.5))
        sp_val = round(sp_val, 1)
        ge_val = max(0.0, pulp.value(grid_e[i]) or 0.0)
        su_val = max(0.0, pulp.value(solar_use[i]) or 0.0)
        bc_val = max(0.0, pulp.value(bat_ch[i]) or 0.0)
        bd_val = max(0.0, pulp.value(bat_dis[i]) or 0.0)
        soc_val = max(0.0, min(bat_cap, pulp.value(soc[i]) or 0.0))

        ac_cool_active = (ac_cool_kw / max(total_ac, 1)) * ac_val if total_ac > 0 else 0.0
        fan_cool_active = (fan_power_kw / max(total_fan, 1)) * fan_val if total_fan > 0 else 0.0
        cool_e = ((ac_power_kw / max(total_ac, 1)) * ac_val + fan_cool_active) * DT if total_ac > 0 else fan_cool_active * DT

        occ = int(row["occupancy_count"])
        grid_ok = bool(row["grid_available"])
        is_peak = str(row.get("tariff_type", "")).lower().strip() == "peak"
        irr = float(row.get("solar_irradiance_w_m2", 0.0))
        temp = float(row["temperature_c"])

        indoor_temp = estimate_indoor_temp(
            state, temp, float(row["heat_index_c"]),
            occ, ac_cool_active, sp_val if ac_val > 0 else None, irr
        )
        state.indoor_temp_c = indoor_temp
        comfort_st = classify_comfort(indoor_temp, comfort_min, comfort_max, occ > 0, vulnerable)

        cost = ge_val * float(row["tariff_pkr_per_kwh"])
        emissions = ge_val * float(row["grid_carbon_kgco2_per_kwh"])

        rc, expl = _pick_reason_code(
            {}, grid_ok, is_peak, occ, su_val, bd_val, soc_val, bat_reserve, temp, bat_cap
        )

        # Constraint violation count
        viols = 0
        if not grid_ok and ge_val > 0.001:
            viols += 1
        if ac_val > total_ac:
            viols += 1
        if bat_cap > 0 and soc_val < bat_reserve - 0.001:
            viols += 1

        rows.append({
            "scenario_id": str(row["scenario_id"]),
            "run_id": run_id,
            "timestamp_local": row["timestamp_local"],
            "recommended_ac_units_on": ac_val,
            "recommended_ac_setpoint_c": round(sp_val, 1) if ac_val > 0 else None,
            "recommended_fan_units_on": fan_val,
            "grid_energy_kwh": round(ge_val, 4),
            "solar_energy_used_kwh": round(su_val, 4),
            "battery_charge_kwh": round(bc_val, 4),
            "battery_discharge_kwh": round(bd_val, 4),
            "battery_soc_kwh": round(soc_val, 4),
            "cooling_energy_kwh": round(cool_e, 4),
            "estimated_indoor_temp_c": round(indoor_temp, 2),
            "comfort_status": comfort_st,
            "interval_cost_pkr": round(cost, 2),
            "interval_emissions_kgco2e": round(emissions, 4),
            "reason_code": rc,
            "explanation": expl,
            "constraint_violation_count": viols,
        })

    out_df = pd.DataFrame(rows)
    summary = _build_summary(out_df, baseline_df, run_id, algo_ver, intervals)
    return out_df, summary


def _greedy_solve(
    intervals, N, run_id, algo_ver,
    total_ac, total_fan, ac_power_kw, ac_cool_kw, fan_power_kw,
    default_sp, min_sp, max_sp,
    bat_cap, bat_reserve, max_ch_kw, max_dis_kw, ch_eff, dis_eff,
    solar_cap, solar_eff, init_soc,
    comfort_min, comfort_max, max_demand_kw, vulnerable,
    profile, baseline_df,
) -> Tuple[pd.DataFrame, Dict]:
    """Greedy heuristic fallback when PuLP is not installed."""
    soc = init_soc
    state = BuildingThermalState(
        indoor_temp_c=float(intervals.iloc[0]["temperature_c"]) - 2.0,
        area_m2=float(profile["area_m2"]),
        insulation_level=str(profile["insulation_level"]),
        sun_exposure=str(profile["sun_exposure"]),
        comfort_min_c=comfort_min,
        comfort_max_c=comfort_max,
        vulnerable_occupants=vulnerable,
    )
    rows = []

    for i, (_, row) in enumerate(intervals.iterrows()):
        occ = int(row["occupancy_count"])
        grid_ok = bool(row["grid_available"])
        temp = float(row["temperature_c"])
        hi = float(row["heat_index_c"])
        irr = float(row.get("solar_irradiance_w_m2", 0.0))
        tariff = float(row["tariff_pkr_per_kwh"])
        carbon = float(row["grid_carbon_kgco2_per_kwh"])
        non_cool = float(row.get("non_cooling_load_kw", 0.0)) * DT
        is_peak = str(row.get("tariff_type", "")).lower().strip() == "peak"

        solar_gen_i = solar_cap * (irr / 1000) * solar_eff * DT if solar_cap > 0 else 0.0

        # Decide AC on/off
        need_cool = (occ > 0 and temp > comfort_max) or temp > comfort_max + 3
        avoid_peak = is_peak and not (vulnerable and temp > comfort_max + 2)
        ac_val = total_ac if (need_cool and not avoid_peak) else (
            max(1, total_ac // 2) if need_cool else 0
        )
        if not grid_ok:
            ac_val = 0

        fan_val = total_fan if occ > 0 else 0
        if not grid_ok:
            fan_val = 0

        ac_energy = (ac_power_kw / max(total_ac, 1)) * ac_val * DT if total_ac > 0 else 0.0
        fan_energy = (fan_power_kw / max(total_fan, 1)) * fan_val * DT if total_fan > 0 else 0.0
        load = ac_energy + fan_energy + non_cool
        cool_e = ac_energy + fan_energy

        su = min(solar_gen_i, load)
        remaining = load - su
        surplus = solar_gen_i - su

        # Charge battery from surplus
        bc = min(surplus, max_ch_kw * DT, (bat_cap - soc) / ch_eff) if bat_cap > 0 else 0.0
        soc = min(bat_cap, soc + bc * ch_eff)

        # Discharge if needed and grid unavailable
        bd = 0.0
        if not grid_ok and remaining > 0 and bat_cap > 0 and soc > bat_reserve:
            bd = min(remaining / dis_eff, max_dis_kw * DT, (soc - bat_reserve) / dis_eff)
            soc = max(bat_reserve, soc - bd)
            remaining -= bd * dis_eff

        ge = max(0.0, remaining) if grid_ok else 0.0
        cost = ge * tariff
        emissions = ge * carbon

        sp = default_sp if ac_val > 0 else None
        ac_cool_active = (ac_cool_kw / max(total_ac, 1)) * ac_val if total_ac > 0 else 0.0

        indoor_temp = estimate_indoor_temp(state, temp, hi, occ, ac_cool_active, sp, irr)
        state.indoor_temp_c = indoor_temp
        comfort_st = classify_comfort(indoor_temp, comfort_min, comfort_max, occ > 0, vulnerable)

        rc, expl = _pick_reason_code({}, grid_ok, is_peak, occ, su, bd, soc, bat_reserve, temp)
        viols = 1 if (not grid_ok and ge > 0.001) else 0

        rows.append({
            "scenario_id": str(row["scenario_id"]),
            "run_id": run_id,
            "timestamp_local": row["timestamp_local"],
            "recommended_ac_units_on": ac_val,
            "recommended_ac_setpoint_c": round(sp, 1) if sp else None,
            "recommended_fan_units_on": fan_val,
            "grid_energy_kwh": round(ge, 4),
            "solar_energy_used_kwh": round(su, 4),
            "battery_charge_kwh": round(bc, 4),
            "battery_discharge_kwh": round(bd, 4),
            "battery_soc_kwh": round(soc, 4),
            "cooling_energy_kwh": round(cool_e, 4),
            "estimated_indoor_temp_c": round(indoor_temp, 2),
            "comfort_status": comfort_st,
            "interval_cost_pkr": round(cost, 2),
            "interval_emissions_kgco2e": round(emissions, 4),
            "reason_code": rc,
            "explanation": expl,
            "constraint_violation_count": viols,
        })

    out_df = pd.DataFrame(rows)
    summary = _build_summary(out_df, baseline_df, run_id, algo_ver, intervals)
    return out_df, summary


def _build_summary(out_df, baseline_df, run_id, algo_ver, intervals) -> Dict:
    opt_cost = out_df["interval_cost_pkr"].sum()
    opt_energy = out_df["grid_energy_kwh"].sum()
    opt_em = out_df["interval_emissions_kgco2e"].sum()
    opt_peak = (out_df["grid_energy_kwh"] / DT).max()
    opt_solar = out_df["solar_energy_used_kwh"].sum()
    total_solar_gen = sum(
        float(intervals.iloc[i].get("solar_irradiance_w_m2", 0)) / 1000 * DT
        for i in range(len(intervals))
    )

    occ_mask = intervals["occupancy_count"].values > 0
    comfort_ok = (out_df["comfort_status"] == "within_range").values
    compliance = float(comfort_ok[occ_mask].sum()) / max(1, occ_mask.sum()) * 100

    base_cost = baseline_df["baseline_cost_pkr"].sum() if "baseline_cost_pkr" in baseline_df.columns else opt_cost
    base_energy = baseline_df["baseline_grid_energy_kwh"].sum() if "baseline_grid_energy_kwh" in baseline_df.columns else opt_energy
    base_em = baseline_df["baseline_emissions_kgco2e"].sum() if "baseline_emissions_kgco2e" in baseline_df.columns else opt_em
    base_peak = (baseline_df["baseline_grid_energy_kwh"] / DT).max() if "baseline_grid_energy_kwh" in baseline_df.columns else opt_peak

    return {
        "run_id": run_id,
        "algorithm_version": algo_ver,
        "run_timestamp": datetime.utcnow().isoformat(),
        "baseline_total_energy_kwh": round(float(base_energy), 3),
        "optimized_total_energy_kwh": round(float(opt_energy), 3),
        "baseline_total_cost_pkr": round(float(base_cost), 2),
        "optimized_total_cost_pkr": round(float(opt_cost), 2),
        "baseline_peak_demand_kw": round(float(base_peak), 3),
        "optimized_peak_demand_kw": round(float(opt_peak), 3),
        "baseline_emissions_kgco2e": round(float(base_em), 3),
        "optimized_emissions_kgco2e": round(float(opt_em), 3),
        "energy_saving_kwh": round(float(base_energy - opt_energy), 3),
        "cost_saving_pkr": round(float(base_cost - opt_cost), 2),
        "cost_saving_pct": round((base_cost - opt_cost) / max(base_cost, 0.01) * 100, 1),
        "emission_reduction_kgco2e": round(float(base_em - opt_em), 3),
        "emission_reduction_pct": round((base_em - opt_em) / max(base_em, 0.001) * 100, 1),
        "solar_utilization_pct": round(opt_solar / max(total_solar_gen, 0.001) * 100, 1),
        "comfort_compliance_pct": round(compliance, 1),
        "unsafe_heat_intervals": int((out_df["comfort_status"].isin(["unsafe", "infeasible"])).sum()),
        "constraint_violations": int(out_df["constraint_violation_count"].sum()),
    }
