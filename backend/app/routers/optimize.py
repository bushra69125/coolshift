import uuid
import time
import math
import logging
import threading
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np

from ..engines.data_loader import load_excel, parse_workbook, fill_missing_heat_index
from ..engines.baseline import compute_baseline, summarize_baseline
from ..engines.optimizer import optimize_schedule
from ..models.schemas import OptimizationRequest
from ..utils.ai_explainer import generate_daily_summary
from ..utils.supabase_client import save_optimization_run

logger = logging.getLogger("coolshift.optimize")
router = APIRouter(prefix="/optimize", tags=["optimize"])


def _extract_assets(assets_df, scenario_id: str) -> dict:
    if assets_df is None or len(assets_df) == 0:
        return {}
    row = assets_df[assets_df["scenario_id"].astype(str) == str(scenario_id)]
    if len(row) == 0:
        return {}
    return row.iloc[0].to_dict()


def _extract_profile(profiles_df, scenario_id: str) -> dict:
    if profiles_df is None or len(profiles_df) == 0:
        return {
            "scenario_id": scenario_id, "name": scenario_id,
            "timezone": "Asia/Karachi", "building_type": "household",
            "area_m2": 100.0, "room_count": 3, "max_occupancy": 5,
            "insulation_level": "medium", "sun_exposure": "medium",
            "comfort_min_c": 22.0, "comfort_max_c": 26.0,
            "vulnerable_occupants": False,
            "budget_pkr_per_day": 500.0, "maximum_grid_demand_kw": 10.0,
        }
    row = profiles_df[profiles_df["scenario_id"].astype(str) == str(scenario_id)]
    if len(row) == 0:
        return {"scenario_id": scenario_id}
    return row.iloc[0].to_dict()


@router.post("/run")
async def run_optimization(
    file: UploadFile = File(...),
    scenario_id: str = "PUB-A",
    days: int = 7,
    weight_cost: float = 0.35,
    weight_emissions: float = 0.30,
    weight_comfort: float = 0.25,
    weight_peak: float = 0.10,
):
    """
    Full end-to-end optimization for a given scenario.
    Returns interval-level schedule + summary metrics.
    """
    t0 = time.time()
    logger.info(f"[RUN] Starting optimization — scenario={scenario_id}, days={days}")

    contents = await file.read()
    logger.info(f"[RUN] File received: {len(contents)/1024:.1f} KB")

    try:
        sheets = load_excel(contents)
        parsed = parse_workbook(sheets)
        logger.info(f"[RUN] Workbook parsed, sheets found: {list(sheets.keys())}")
    except Exception as e:
        logger.error(f"[RUN] ❌ Workbook parse error: {e}")
        raise HTTPException(400, f"Cannot parse workbook: {e}")

    intervals_all = parsed.get("intervals")
    if intervals_all is None:
        logger.error("[RUN] ❌ No interval_inputs sheet found")
        raise HTTPException(400, "No interval data in workbook")

    logger.info(f"[RUN] Total interval records loaded: {len(intervals_all)}")

    intervals_all = fill_missing_heat_index(intervals_all)
    intervals_all["scenario_id"] = intervals_all["scenario_id"].astype(str)

    mask = intervals_all["scenario_id"] == str(scenario_id)
    intervals = intervals_all[mask].copy()

    if len(intervals) == 0:
        available = intervals_all["scenario_id"].unique().tolist()
        logger.error(f"[RUN] ❌ Scenario '{scenario_id}' not found. Available: {available}")
        raise HTTPException(404, f"Scenario '{scenario_id}' not found. Available: {available}")

    intervals = intervals.sort_values("timestamp_local").head(days * 96)
    logger.info(f"[RUN] Scenario '{scenario_id}': {len(intervals)} intervals selected ({days} days)")

    profile = _extract_profile(parsed.get("profiles"), scenario_id)
    appliances = parsed.get("appliances", pd.DataFrame())
    if appliances is not None and len(appliances) > 0:
        appliances = appliances[appliances["scenario_id"].astype(str) == str(scenario_id)]

    assets = _extract_assets(parsed.get("assets"), scenario_id)
    baseline_sched = parsed.get("baseline")

    run_id = str(uuid.uuid4())
    logger.info(f"[RUN] Run ID: {run_id}")

    logger.info("[RUN] Computing baseline...")
    baseline_df = compute_baseline(
        profile, appliances if appliances is not None else pd.DataFrame(),
        intervals, assets, baseline_sched
    )
    logger.info(f"[RUN] ✅ Baseline done — cost: {baseline_df['baseline_cost_pkr'].sum():.2f} PKR")

    weights = {
        "cost": weight_cost,
        "emissions": weight_emissions,
        "comfort": weight_comfort,
        "peak_demand": weight_peak,
    }
    logger.info(f"[RUN] Running LP optimizer with weights: {weights}")

    out_df, summary = optimize_schedule(
        profile, appliances if appliances is not None else pd.DataFrame(),
        intervals, assets, baseline_df, weights, run_id=run_id,
    )

    elapsed = time.time() - t0
    logger.info(f"[RUN] ✅ Optimization complete in {elapsed:.1f}s")
    logger.info(f"[RUN]    Intervals: {len(out_df)}")
    logger.info(f"[RUN]    Cost saving: {summary.get('cost_saving_pct', 0):.1f}%  ({summary.get('cost_saving_pkr', 0):.2f} PKR)")
    logger.info(f"[RUN]    Emission reduction: {summary.get('emission_reduction_pct', 0):.1f}%")
    logger.info(f"[RUN]    Comfort compliance: {summary.get('comfort_compliance_pct', 0):.1f}%")
    logger.info(f"[RUN]    Constraint violations: {summary.get('constraint_violations', 0)}")

    baseline_summary = summarize_baseline(baseline_df)

    # Replace NaN/Inf with None so JSONResponse doesn't crash
    out_df = out_df.replace([np.nan, np.inf, -np.inf], None)
    schedule_records = out_df.where(pd.notnull(out_df), other=None).to_dict(orient="records")

    def _clean(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v

    summary_clean = {k: _clean(v) for k, v in summary.items()}
    baseline_clean = {k: _clean(v) for k, v in baseline_summary.items()}

    # Groq AI: generate a natural-language summary for this run
    try:
        ai_summary = generate_daily_summary(
            scenario_id=scenario_id,
            date=str(summary.get("run_timestamp", "")[:10]),
            total_cost=float(summary.get("optimized_total_cost_pkr") or 0),
            baseline_cost=float(summary.get("baseline_total_cost_pkr") or 0),
            total_energy=float(summary.get("optimized_total_energy_kwh") or 0),
            peak_demand=float(summary.get("optimized_peak_demand_kw") or 0),
            emissions=float(summary.get("optimized_emissions_kgco2e") or 0),
            comfort_pct=float(summary.get("comfort_compliance_pct") or 0),
            solar_pct=float(summary.get("solar_utilization_pct") or 0),
        )
        logger.info(f"[RUN] ✅ Groq AI summary generated ({len(ai_summary)} chars)")
    except Exception as e:
        logger.warning(f"[RUN] Groq AI failed (non-critical): {e}")
        ai_summary = f"Scenario {scenario_id}: Saved PKR {summary.get('cost_saving_pkr', 0):.0f} ({summary.get('cost_saving_pct', 0):.1f}%) vs baseline with {summary.get('comfort_compliance_pct', 0):.0f}% comfort compliance."

    # Supabase: save run summary in background thread (non-blocking)
    weights = {"cost": weight_cost, "emissions": weight_emissions, "comfort": weight_comfort, "peak_demand": weight_peak}
    threading.Thread(
        target=save_optimization_run,
        args=(run_id, scenario_id, summary, days, weights),
        daemon=True,
    ).start()

    return JSONResponse({
        "run_id": run_id,
        "scenario_id": scenario_id,
        "intervals_optimized": len(out_df),
        "comfort_min": float(profile.get("comfort_min_c", 22)),
        "comfort_max": float(profile.get("comfort_max_c", 26)),
        "ai_summary": ai_summary,
        "summary": summary_clean,
        "baseline_summary": baseline_clean,
        "schedule": schedule_records,
    })


@router.post("/all-scenarios")
async def optimize_all_scenarios(file: UploadFile = File(...), days: int = 7):
    """Process all 3 public scenarios + return combined output (2016+ rows)."""
    contents = await file.read()
    sheets = load_excel(contents)
    parsed = parse_workbook(sheets)
    intervals_all = parsed.get("intervals")
    if intervals_all is None:
        raise HTTPException(400, "No interval data")

    intervals_all = fill_missing_heat_index(intervals_all)
    intervals_all["scenario_id"] = intervals_all["scenario_id"].astype(str)
    scenario_ids = intervals_all["scenario_id"].unique().tolist()

    results = {}
    for sid in scenario_ids:
        mask = intervals_all["scenario_id"] == sid
        intervals = intervals_all[mask].sort_values("timestamp_local").head(days * 96).copy()
        if len(intervals) == 0:
            continue

        profile = _extract_profile(parsed.get("profiles"), sid)
        appliances = parsed.get("appliances", pd.DataFrame())
        if appliances is not None and len(appliances) > 0:
            appliances = appliances[appliances["scenario_id"].astype(str) == sid]
        assets = _extract_assets(parsed.get("assets"), sid)

        baseline_df = compute_baseline(
            profile, appliances if appliances is not None else pd.DataFrame(),
            intervals, assets, parsed.get("baseline")
        )
        out_df, summary = optimize_schedule(
            profile, appliances if appliances is not None else pd.DataFrame(),
            intervals, assets, baseline_df,
            {"cost": 0.35, "emissions": 0.30, "comfort": 0.25, "peak_demand": 0.10}
        )
        results[sid] = {
            "summary": summary,
            "baseline_summary": summarize_baseline(baseline_df),
            "row_count": len(out_df),
            "schedule_sample": out_df.head(5).to_dict(orient="records"),
        }

    return JSONResponse({"scenarios_processed": list(results.keys()), "results": results})
