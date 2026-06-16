from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
import pandas as pd
import math
import numpy as np

from ..engines.data_loader import load_excel, parse_workbook, fill_missing_heat_index
from ..engines.baseline import compute_baseline, summarize_baseline
from ..engines.optimizer import optimize_schedule
from ..utils.export import export_interval_csv, export_summary_excel
from .optimize import _extract_profile, _extract_assets

router = APIRouter(prefix="/export", tags=["export"])


def _safe_appliances(apps) -> pd.DataFrame:
    """Return appliances DataFrame safely — avoids DataFrame boolean ambiguity."""
    if apps is None:
        return pd.DataFrame()
    if isinstance(apps, pd.DataFrame):
        return apps
    return pd.DataFrame()


@router.post("/csv/{scenario_id}")
async def export_csv(scenario_id: str, file: UploadFile = File(...), days: int = 7):
    contents = await file.read()
    sheets = load_excel(contents)
    parsed = parse_workbook(sheets)
    intervals_all = fill_missing_heat_index(parsed.get("intervals"))
    intervals_all["scenario_id"] = intervals_all["scenario_id"].astype(str)

    intervals = intervals_all[intervals_all["scenario_id"] == scenario_id].sort_values("timestamp_local").head(days * 96)
    if len(intervals) == 0:
        raise HTTPException(404, f"Scenario '{scenario_id}' not found")

    profile = _extract_profile(parsed.get("profiles"), scenario_id)
    raw_apps = parsed.get("appliances")
    if isinstance(raw_apps, pd.DataFrame) and len(raw_apps) > 0:
        appliances = raw_apps[raw_apps["scenario_id"].astype(str) == scenario_id]
    else:
        appliances = pd.DataFrame()
    assets = _extract_assets(parsed.get("assets"), scenario_id)

    baseline_df = compute_baseline(profile, appliances, intervals, assets)
    out_df, _ = optimize_schedule(
        profile, appliances, intervals, assets, baseline_df,
        {"cost": 0.35, "emissions": 0.30, "comfort": 0.25, "peak_demand": 0.10}
    )

    csv_bytes = export_interval_csv(out_df)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=coolshift_{scenario_id}_{days}d.csv"}
    )


@router.post("/excel-all")
async def export_all_excel(file: UploadFile = File(...), days: int = 7):
    """Export all scenarios as a multi-sheet Excel file (2,016+ rows)."""
    contents = await file.read()
    sheets = load_excel(contents)
    parsed = parse_workbook(sheets)
    intervals_all = fill_missing_heat_index(parsed.get("intervals"))
    intervals_all["scenario_id"] = intervals_all["scenario_id"].astype(str)

    interval_dfs = {}
    summaries = {}

    raw_apps = parsed.get("appliances")

    for sid in intervals_all["scenario_id"].unique():
        intervals = intervals_all[intervals_all["scenario_id"] == sid].sort_values("timestamp_local").head(days * 96).copy()
        if len(intervals) == 0:
            continue

        profile = _extract_profile(parsed.get("profiles"), sid)
        if isinstance(raw_apps, pd.DataFrame) and len(raw_apps) > 0:
            appliances = raw_apps[raw_apps["scenario_id"].astype(str) == sid]
        else:
            appliances = pd.DataFrame()
        assets = _extract_assets(parsed.get("assets"), sid)

        baseline_df = compute_baseline(profile, appliances, intervals, assets)
        out_df, summary = optimize_schedule(
            profile, appliances, intervals, assets, baseline_df,
            {"cost": 0.35, "emissions": 0.30, "comfort": 0.25, "peak_demand": 0.10}
        )

        # Clean NaN/Inf before storing
        out_df = out_df.replace([np.nan, np.inf, -np.inf], None)
        interval_dfs[sid] = out_df
        summaries[sid] = {k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
                          for k, v in summary.items()}

    if not interval_dfs:
        raise HTTPException(500, "No scenarios could be optimized")

    excel_bytes = export_summary_excel(interval_dfs, summaries)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=coolshift_all_scenarios.xlsx"}
    )
